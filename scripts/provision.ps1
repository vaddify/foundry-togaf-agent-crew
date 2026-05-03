<#
  One-time provisioning for ai-startup-team on Microsoft Foundry.
  Creates:
    - Resource group
    - Azure AI Foundry resource (AI Services, multi-service)
    - Foundry project
    - Azure Container Registry (for the hosted-agent image)
    - Azure AI Search (vector memory)
    - Model deployments (5)
  After this finishes, add a Bing grounding connection in the Foundry portal
  (Foundry project > Connections > + New > Grounding with Bing Search).

  Verified against eastus2 model catalog on the date of writing.
#>

param(
  [string]$Subscription = "52b8df4d-506e-4b20-9ee7-d90289c7280b",
  [string]$ResourceGroup = "rg-ai-startup-team",
  [string]$Region        = "eastus2",
  [string]$FoundryName   = "fnd-ai-startup-team",
  [string]$ProjectName   = "ai-startup-team",
  [string]$AcrName       = "acraistartupteam$(Get-Random -Maximum 9999)",
  [string]$SearchName    = "srch-ai-startup-team-$(Get-Random -Maximum 9999)"
)

$ErrorActionPreference = "Stop"

az account set --subscription $Subscription
az group create -n $ResourceGroup -l $Region | Out-Null

Write-Host "==> Foundry (AI Services) resource"
az cognitiveservices account create `
  -n $FoundryName -g $ResourceGroup -l $Region `
  --kind AIServices --sku S0 --yes | Out-Null

Write-Host "==> Foundry project"
az ai project create `
  --name $ProjectName --resource-group $ResourceGroup `
  --account-name $FoundryName | Out-Null

Write-Host "==> ACR"
az acr create -n $AcrName -g $ResourceGroup --sku Basic --admin-enabled true | Out-Null

Write-Host "==> Azure AI Search (vector memory)"
az search service create -n $SearchName -g $ResourceGroup --sku basic | Out-Null

# -------- Model deployments --------
# Versions/SKUs verified via:
#   az cognitiveservices model list --location eastus2
# Capacity values are conservative starting points; raise via the portal
# if you hit rate limits during evals.
Write-Host "==> Model deployments"
$models = @(
  @{ name="gpt-5";              format="OpenAI";    version="2025-08-07"; sku="GlobalStandard"; capacity=20 },
  @{ name="o4-mini";            format="OpenAI";    version="2025-04-16"; sku="GlobalStandard"; capacity=20 },
  @{ name="gpt-4.1";            format="OpenAI";    version="2025-04-14"; sku="GlobalStandard"; capacity=20 },
  @{ name="gpt-4.1-mini";       format="OpenAI";    version="2025-04-14"; sku="GlobalStandard"; capacity=50 },
  @{ name="claude-sonnet-4-5";  format="Anthropic"; version="20250929";   sku="GlobalStandard"; capacity=10 }
)
foreach ($m in $models) {
  Write-Host "   - $($m.name) ($($m.version), $($m.sku), cap=$($m.capacity))"
  az cognitiveservices account deployment create `
    -g $ResourceGroup -n $FoundryName `
    --deployment-name $m.name `
    --model-name $m.name --model-format $m.format --model-version $m.version `
    --sku-name $m.sku --sku-capacity $m.capacity | Out-Null
}

Write-Host ""
Write-Host "==> Done. Next:"
Write-Host "   1. In the Foundry portal: project > Connections > + New > Grounding with Bing Search"
Write-Host "   2. Update .foundry/agent-metadata.yaml with the printed endpoints (see below)"
Write-Host "   3. Copy .env.example to .env and fill in AZURE_AI_PROJECT_ENDPOINT + AZURE_SEARCH_ENDPOINT"
Write-Host ""
Write-Host "==> Useful endpoints:"
$projEndpoint = az cognitiveservices account show -g $ResourceGroup -n $FoundryName --query "properties.endpoint" -o tsv
$searchEndpoint = "https://$SearchName.search.windows.net"
$acrLoginServer = "$AcrName.azurecr.io"
Write-Host "   AZURE_AI_PROJECT_ENDPOINT = $projEndpoint"
Write-Host "   AZURE_SEARCH_ENDPOINT      = $searchEndpoint"
Write-Host "   ACR_LOGIN_SERVER           = $acrLoginServer"