<#
.SYNOPSIS
  One-shot script to publish ai-startup-team to GitHub.

.DESCRIPTION
  Initializes a git repo (if not already), creates the remote on GitHub via
  the `gh` CLI, commits everything respecting .gitignore, and pushes `main`.

  DRY-RUN BY DEFAULT. Re-run with -Execute to actually do anything.

  Prereqs:
    - git installed             (winget install --id Git.Git)
    - gh CLI installed + auth'd (winget install --id GitHub.cli ; gh auth login)

  Safety rails:
    - Refuses to run if .env exists and is NOT git-ignored.
    - Refuses to push if any tracked file matches a likely-secret pattern.
    - Will not force-push.
    - Defaults Visibility to "private" so you control when the repo goes public.

.PARAMETER RepoName
  Name of the GitHub repo to create. Defaults to the folder name.

.PARAMETER Owner
  GitHub user or org. Leave blank to use your authenticated `gh` user.

.PARAMETER Visibility
  private | public | internal. Default: private.

.PARAMETER Branch
  Branch name to push. Default: main.

.PARAMETER Execute
  Required to actually run. Without it, every step is logged as DRY-RUN.

.EXAMPLE
  ./scripts/publish-to-github.ps1                        # dry-run preview
  ./scripts/publish-to-github.ps1 -Execute               # really publish (private)
  ./scripts/publish-to-github.ps1 -Visibility public -Execute
#>

[CmdletBinding()]
param(
  [string] $RepoName   = (Split-Path -Leaf (Get-Location)),
  [string] $Owner      = "",
  [ValidateSet("private","public","internal")]
  [string] $Visibility = "private",
  [string] $Branch     = "main",
  [switch] $Execute
)

$ErrorActionPreference = "Stop"

function Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Run($cmd) {
  if ($Execute) {
    Write-Host "    $ $cmd" -ForegroundColor DarkGray
    Invoke-Expression $cmd
  } else {
    Write-Host "    [DRY-RUN] $cmd" -ForegroundColor Yellow
  }
}

# ---------------------------------------------------------------------------
# 0. Sanity checks
# ---------------------------------------------------------------------------
Step "Sanity checks"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "git not found. Install with: winget install --id Git.Git"
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  throw "gh CLI not found. Install with: winget install --id GitHub.cli ; then run: gh auth login"
}

# .env must not be tracked. If it exists, .gitignore must cover it.
if (Test-Path .env) {
  if (Test-Path .git) {
    & git check-ignore -q .env 2>$null
    $ignored = ($LASTEXITCODE -eq 0)
  } else {
    # No git repo yet; trust the .gitignore file content
    $ignored = (Select-String -Path .gitignore -Pattern '^\.env(\s|$)' -Quiet)
  }
  if (-not $ignored) {
    throw ".env exists but is NOT git-ignored. Refusing to continue (would leak secrets)."
  }
  Write-Host "    .env present and git-ignored - OK"
}

# Block obvious accidental secrets in the working tree (excluding .env*).
$leakHits = @()
$patterns = 'AZURE_.*KEY','AZURE_.*SECRET','BEGIN PRIVATE KEY','sk-[A-Za-z0-9]{20,}','ghp_[A-Za-z0-9]{20,}'
$candidateFiles = Get-ChildItem -Recurse -File -Force `
    | Where-Object { $_.FullName -notmatch '\\(\.git|\.venv|venv|node_modules|__pycache__|dist|build|\.foundry\\results)\\' `
        -and $_.Name -notlike '.env*' `
        -and $_.Name -ne 'publish-to-github.ps1' `
        -and $_.Length -lt 1MB }
foreach ($p in $patterns) {
  $hit = $candidateFiles | Select-String -Pattern $p -List -ErrorAction SilentlyContinue
  if ($hit) { $leakHits += $hit }
}
if ($leakHits.Count -gt 0) {
  Write-Host "Potential secret(s) detected in working tree:" -ForegroundColor Red
  $leakHits | ForEach-Object { Write-Host "    $($_.Path):$($_.LineNumber)" -ForegroundColor Red }
  throw "Refusing to publish. Remove or redact, then re-run."
}
Write-Host "    No obvious secrets in working tree â€” OK"

# ---------------------------------------------------------------------------
# 1. git init + initial commit (idempotent)
# ---------------------------------------------------------------------------
Step "Git repo init"

if (-not (Test-Path .git)) {
  Run "git init -b $Branch"
} else {
  Write-Host "    .git already present â€” skipping init"
}

# Configure identity if not already set globally
$cfgEmail = (& git config --get user.email) 2>$null
$cfgName  = (& git config --get user.name)  2>$null
if (-not $cfgEmail -or -not $cfgName) {
  Write-Host "    NOTE: git user.name / user.email not set globally."
  Write-Host "          Run once: git config --global user.email you@example.com"
  Write-Host "                    git config --global user.name  ""Your Name"""
}

Run "git add ."
# `git commit` is allowed to no-op if nothing changed
if ($Execute) {
  & git diff --cached --quiet
  if ($LASTEXITCODE -ne 0) {
    & git commit -m "Initial commit: ai-startup-team (5-agent TOGAF crew on Microsoft Foundry)"
  } else {
    Write-Host "    Nothing to commit"
  }
} else {
  Write-Host "    [DRY-RUN] git commit -m ""Initial commit: ai-startup-team ..."""
}

# ---------------------------------------------------------------------------
# 2. Create remote on GitHub via gh
# ---------------------------------------------------------------------------
Step "Create GitHub repo ($Visibility)"

# If gh is not yet authenticated, bail with guidance â€” never auto-login.
if ($Execute) {
  & gh auth status 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "gh CLI is not authenticated. Run: gh auth login"
  }
}

$fullName = if ($Owner) { "$Owner/$RepoName" } else { $RepoName }

# Check if the remote repo already exists; if so, just add it as origin.
$exists = $false
if ($Execute) {
  & gh repo view $fullName 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { $exists = $true }
}

if ($exists) {
  Write-Host "    Remote $fullName already exists â€” will add as origin and push."
  $remoteUrl = (& gh repo view $fullName --json url -q .url)
  Run "git remote remove origin 2>$null; git remote add origin $remoteUrl"
} else {
  # --source=. uses current dir; --push pushes after create; we omit --push
  # so this script can stage the push step explicitly with safety checks.
  $createCmd = "gh repo create $fullName --$Visibility --source=. --remote=origin --description ""5-agent TOGAF founding crew on Microsoft Foundry: market research, architecture review, MVP scaffolding, delivery plan, GTM drafts. Multi-model (GPT-5, Claude Sonnet 4.5, o4-mini, GPT-4.1) orchestrated with Microsoft Agent Framework; deployed to Azure Container Apps; evaluated with azure-ai-evaluation; distributed to Teams via Copilot Studio."""
  Run $createCmd
}

# ---------------------------------------------------------------------------
# 3. Push (no force, ever)
# ---------------------------------------------------------------------------
Step "Push to origin/$Branch"
Run "git branch -M $Branch"
Run "git push -u origin $Branch"

# ---------------------------------------------------------------------------
# 4. Friendly summary
# ---------------------------------------------------------------------------
Step "Done"
if ($Execute) {
  $url = (& gh repo view $fullName --json url -q .url)
  Write-Host "    Repo: $url"
  Write-Host "    Open with: gh repo view --web"
} else {
  Write-Host "    DRY-RUN complete. Re-run with -Execute to publish for real."
}