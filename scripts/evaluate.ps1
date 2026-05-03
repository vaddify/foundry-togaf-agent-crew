<#
  Real batch eval wrapper. Calls src/orchestrator/evaluate.py via the venv.

  Examples:
    ./scripts/evaluate.ps1                           # local mode, full golden set
    ./scripts/evaluate.ps1 -Limit 3                  # smoke test 3 prompts
    ./scripts/evaluate.ps1 -EndpointUrl https://...  # hit deployed Container App
#>

param(
  [ValidateSet("local","endpoint")]
  [string]$Mode = "local",
  [string]$EndpointUrl = "",
  [string]$Dataset = ".foundry/datasets/golden-set.jsonl",
  [int]$Limit = 0,
  [string]$JudgeModel = ""
)

$ErrorActionPreference = "Stop"

$py = Join-Path (Resolve-Path ".").Path ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "venv not found at $py - run: uv venv && uv pip install -e ." }

$env:PYTHONIOENCODING = "utf-8"

$args = @("-m", "src.orchestrator.evaluate", "--mode", $Mode, "--dataset", $Dataset)
if ($EndpointUrl)        { $args += @("--endpoint-url", $EndpointUrl) }
if ($Limit -gt 0)        { $args += @("--limit", "$Limit") }
if ($JudgeModel)         { $args += @("--judge-model", $JudgeModel) }

Write-Host "==> $py $($args -join ' ')"
& $py @args
