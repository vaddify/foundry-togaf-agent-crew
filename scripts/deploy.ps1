<#
  Real deploy: build container in ACR, push, deploy as Azure Container App.

  Idempotent. Safe to re-run. Uses ONLY real az CLI commands:
    - az acr build              (ACR cloud build, no local Docker needed)
    - az containerapp env       (Container Apps environment)
    - az containerapp create    (or update) the app
    - az role assignment        (grant managed identity access)

  Reads names from .foundry/agent-metadata.yaml.
  Reads runtime env vars from .env (gitignored).

  Exposes a public HTTPS endpoint:
    https://<app-name>.<env-default-domain>/invocations
#>

param(
  [string]$Environment = "dev",
  [string]$Tag         = (Get-Date -Format "yyyyMMddHHmm")
)

$ErrorActionPreference = "Continue"

# az writes harmless WARNINGs to stderr; under PowerShell + Stop that aborts.
# We use Continue and check $LASTEXITCODE manually after each az call.
$PSNativeCommandUseErrorActionPreference = $false   # no-op on PS 5.1, helps PS 7+

# az acr build/log streams emoji + ANSI escapes; PS 5.1 default cp1252 stdout
# blows up on those. Force UTF-8 for both .NET console and Python child procs.
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING     = "utf-8"
$env:AZURE_CORE_NO_COLOR  = "1"      # tell az to skip ANSI color where possible

function Invoke-AzOrDie {
  param([Parameter(Mandatory)][scriptblock]$Block, [string]$What = "az command")
  & $Block 2>&1 | ForEach-Object { Write-Host $_ }
  if ($LASTEXITCODE -ne 0) { throw "FAILED: $What (exit $LASTEXITCODE)" }
}

# --- read .foundry/agent-metadata.yaml ---
$meta = Get-Content ".foundry/agent-metadata.yaml" -Raw
function Get-MetaValue($key) {
  return ($meta | Select-String -Pattern "$key`:\s*(\S+)" -AllMatches).Matches[0].Groups[1].Value
}
$acr     = Get-MetaValue "azureContainerRegistry"
$rg      = Get-MetaValue "resourceGroup"
$proj    = Get-MetaValue "projectEndpoint"
$name    = Get-MetaValue "agentName"
$region  = Get-MetaValue "region"
$subId   = Get-MetaValue "subscriptionId"

$envName  = "cae-ai-startup-team"
$logName  = "log-ai-startup-team"
$image    = "$acr.azurecr.io/ai-startup-team:$Tag"
$appName  = $name      # ai-startup-team

Write-Host "==> Verifying Azure context"
az account set --subscription $subId | Out-Null

# --- 1. ACR cloud build (use --no-logs to avoid the cp1252 streaming bug
#       in the Windows az CLI; we poll for completion instead) ---
Write-Host "==> Building $image (az acr build --no-logs)"
Invoke-AzOrDie -What "az acr build queue" -Block {
  az acr build -r $acr -t "ai-startup-team:$Tag" -f src/orchestrator/Dockerfile --no-logs .
}
Write-Host "==> Waiting for build to finish (polling)..."
$lastStatus = ""
while ($true) {
  Start-Sleep -Seconds 15
  $status = az acr task list-runs -r $acr --top 1 --query "[0].status" -o tsv 2>$null
  if ($status -ne $lastStatus) { Write-Host "   status: $status"; $lastStatus = $status }
  if ($status -in @("Succeeded","Failed","Canceled","Error","Timeout")) { break }
}
if ($status -ne "Succeeded") { throw "ACR build did not succeed (status=$status)" }

# --- 2. Log Analytics workspace (Container Apps env requires one) ---
Write-Host "==> Ensuring Log Analytics workspace $logName"
$logId = az monitor log-analytics workspace show -g $rg -n $logName --query customerId -o tsv 2>$null
if (-not $logId) {
  az monitor log-analytics workspace create -g $rg -n $logName -l $region | Out-Null
  $logId = az monitor log-analytics workspace show -g $rg -n $logName --query customerId -o tsv
}
$logKey = az monitor log-analytics workspace get-shared-keys -g $rg -n $logName --query primarySharedKey -o tsv

# --- 3. Container Apps environment ---
Write-Host "==> Ensuring Container Apps environment $envName"
$envExists = az containerapp env show -g $rg -n $envName --query name -o tsv 2>$null
if (-not $envExists) {
  az containerapp env create `
    -g $rg -n $envName -l $region `
    --logs-workspace-id $logId `
    --logs-workspace-key $logKey | Out-Null
}

# --- 4. Read .env into key=value pairs for the container ---
Write-Host "==> Reading .env"
if (-not (Test-Path ".env")) { throw ".env not found. Copy from .env.example and fill in values." }
$envVars = @()
foreach ($line in (Get-Content ".env")) {
  $trim = $line.Trim()
  if ($trim -eq "" -or $trim.StartsWith("#")) { continue }
  if ($trim -match '^([A-Z_][A-Z0-9_]*)=(.*)$') {
    $k = $matches[1]
    $v = $matches[2]
    # Strip trailing inline comment (   # ...) if present and value isn't quoted
    if ($v -notmatch '^["'']') {
      $v = ($v -replace '\s+#.*$', '')
    }
    $v = $v.Trim().Trim('"').Trim("'")
    if ($v -eq "") { continue }    # skip empty values; let SDK rely on defaults
    $envVars += "$k=$v"
  }
}
# Always set PORT so uvicorn binds correctly
$envVars += "PORT=8080"

# --- 5. Create or update the container app ---
$appExists = az containerapp show -g $rg -n $appName --query name -o tsv 2>$null

if (-not $appExists) {
  Write-Host "==> Creating container app $appName (with system-assigned identity)"
  Invoke-AzOrDie -What "containerapp create" -Block {
    az containerapp create `
      -g $rg -n $appName `
      --environment $envName `
      --image $image `
      --target-port 8080 `
      --ingress external `
      --system-assigned `
      --min-replicas 1 --max-replicas 3 `
      --cpu 1.0 --memory 2.0Gi `
      --registry-server "$acr.azurecr.io" `
      --registry-identity system `
      --env-vars $envVars
  }

  # Grant the app's managed identity AcrPull on the registry
  $principalId = az containerapp show -g $rg -n $appName --query identity.principalId -o tsv
  $acrId = az acr show -n $acr -g $rg --query id -o tsv
  Write-Host "==> Granting AcrPull to managed identity $principalId"
  az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal `
    --role AcrPull --scope $acrId | Out-Null

  # Grant the app's managed identity Cognitive Services User on the Foundry account
  # so it can call deployed models via FoundryChatClient.
  $foundryAccount = "fnd-ai-startup-team"
  $foundryId = az cognitiveservices account show -g $rg -n $foundryAccount --query id -o tsv
  Write-Host "==> Granting Cognitive Services User on $foundryAccount to managed identity"
  az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal `
    --role "Cognitive Services User" --scope $foundryId | Out-Null

  # Re-issue a revision now that role assignments exist (so the new revision
  # actually has permission to pull and call models).
  Write-Host "==> Refreshing revision so new role grants take effect"
  az containerapp update -g $rg -n $appName --image $image --set-env-vars $envVars | Out-Null
}
else {
  Write-Host "==> Updating container app $appName to image $image"
  az containerapp update -g $rg -n $appName `
    --image $image `
    --set-env-vars $envVars | Out-Null
}

# --- 6. Print public endpoint ---
$fqdn = az containerapp show -g $rg -n $appName --query properties.configuration.ingress.fqdn -o tsv
Write-Host ""
Write-Host "===================================================================="
Write-Host " Deployed: https://$fqdn"
Write-Host "   Health:     https://$fqdn/health"
Write-Host "   Invoke:     POST https://$fqdn/invocations"
Write-Host "                 body: {`"input`": `"<your idea>`"}"
Write-Host "===================================================================="
Write-Host ""
Write-Host "Smoke test:"
Write-Host "  curl https://$fqdn/health"
Write-Host "  curl -X POST https://$fqdn/invocations -H 'Content-Type: application/json' -d '{\`"input\`": \`"AI tutor for first-year college calculus students\`"}'"
Write-Host ""
Write-Host "Run evals:"
Write-Host "  ./scripts/evaluate.ps1 -EndpointUrl https://$fqdn"
