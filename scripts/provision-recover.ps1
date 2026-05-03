# Recovery script: completes what provision.ps1 couldn't.
# - Foundry + RG already exist; idempotent for those.
# - Creates Foundry project with the correct CLI command
# - Retries ACR (resource provider now registered)
# - Retries Search in 'eastus' (eastus2 is out of capacity)
# - Deploys the 4 OpenAI models (skips Anthropic; portal for that)
# - Prints the real project endpoint at the end

$ErrorActionPreference = 'Continue'   # we want to see all errors, not stop on first

$Subscription   = '52b8df4d-506e-4b20-9ee7-d90289c7280b'
$ResourceGroup  = 'rg-ai-startup-team'
$Region         = 'eastus2'
$SearchRegion   = 'eastus'             # fallback because eastus2 is out of capacity
$FoundryName    = 'fnd-ai-startup-team'
$ProjectName    = 'ai-startup-team'
$AcrName        = 'acraistartupteam3224'           # reuse name attempted earlier
$SearchName     = 'srch-ai-startup-team-6565'      # reuse name attempted earlier

az account set --subscription $Subscription | Out-Null

# 1. Foundry project -------------------------------------------------------
Write-Host "==> Foundry project"
az cognitiveservices account project create `
  --name $FoundryName `
  --project-name $ProjectName `
  --resource-group $ResourceGroup `
  --location $Region | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "   (project may already exist - continuing)" }

# 2. ACR -------------------------------------------------------------------
Write-Host "==> ACR ($AcrName)"
az acr create -n $AcrName -g $ResourceGroup --sku Basic --admin-enabled true --location $Region | Out-Null

# 3. Azure AI Search in eastus (capacity issue in eastus2) -----------------
Write-Host "==> Azure AI Search ($SearchName in $SearchRegion)"
az search service create -n $SearchName -g $ResourceGroup --sku basic --location $SearchRegion | Out-Null

# 4. OpenAI model deployments ---------------------------------------------
# Anthropic / Claude is intentionally skipped here - it requires marketplace
# provider data (industry/org/country) that the CLI cannot supply
# interactively. Add it from the Foundry portal:
#   Foundry portal > project > Models + endpoints > Deploy > claude-sonnet-4-5
Write-Host "==> Model deployments (OpenAI only)"
$models = @(
  @{ name='gpt-5';        format='OpenAI'; version='2025-08-07'; sku='GlobalStandard'; capacity=20 },
  @{ name='o4-mini';      format='OpenAI'; version='2025-04-16'; sku='GlobalStandard'; capacity=20 },
  @{ name='gpt-4.1';      format='OpenAI'; version='2025-04-14'; sku='GlobalStandard'; capacity=20 },
  @{ name='gpt-4.1-mini'; format='OpenAI'; version='2025-04-14'; sku='GlobalStandard'; capacity=50 }
)
foreach ($m in $models) {
  Write-Host "   - $($m.name)"
  az cognitiveservices account deployment create `
    -g $ResourceGroup -n $FoundryName `
    --deployment-name $m.name `
    --model-name $m.name --model-format $m.format --model-version $m.version `
    --sku-name $m.sku --sku-capacity $m.capacity | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Host "     (failed or already exists - continuing)" }
}

# 5. Print real endpoints --------------------------------------------------
Write-Host ""
Write-Host "==> Endpoints"
$accountEndpoint = az cognitiveservices account show -g $ResourceGroup -n $FoundryName --query "properties.endpoint" -o tsv
$projectEndpoint = az cognitiveservices account project show -g $ResourceGroup --name $FoundryName --project-name $ProjectName --query "properties.endpoints.\`"AI Foundry API\`"" -o tsv 2>$null
$searchEndpoint  = "https://$SearchName.search.windows.net"
$acrLoginServer  = "$AcrName.azurecr.io"

Write-Host "   ACCOUNT_ENDPOINT          = $accountEndpoint"
Write-Host "   AZURE_AI_PROJECT_ENDPOINT = $projectEndpoint"
Write-Host "   AZURE_SEARCH_ENDPOINT     = $searchEndpoint"
Write-Host "   ACR_LOGIN_SERVER          = $acrLoginServer"

Write-Host ""
Write-Host "==> Manual portal steps still to do:"
Write-Host "   1. Foundry portal -> project '$ProjectName' -> Models + endpoints -> + Deploy -> claude-sonnet-4-5 (accept marketplace terms)"
Write-Host "   2. Foundry portal -> project '$ProjectName' -> Connections -> + New -> Grounding with Bing Search"
