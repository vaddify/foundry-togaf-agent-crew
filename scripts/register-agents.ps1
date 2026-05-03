<#
  Register the 5 TOGAF sub-agents as Foundry Persistent Agents.
  Idempotent: re-running creates a new version of each agent.
#>
$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$py = Join-Path (Resolve-Path ".").Path ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "venv not found at $py" }

& $py -m src.orchestrator.register_agents
if ($LASTEXITCODE -ne 0) { throw "register_agents failed (exit $LASTEXITCODE)" }
