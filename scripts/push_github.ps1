# Create GitHub repo and push (run after: gh auth login)
# Usage: powershell -File scripts\push_github.ps1 [-Private]

param(
  [string]$Name = "aegis-ids",
  [switch]$Private
)

$ErrorActionPreference = "Stop"
$gh = "$env:ProgramFiles\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) {
  $gh = "gh"
}

& $gh auth status
if ($LASTEXITCODE -ne 0) {
  Write-Host "Not logged in. Run: gh auth login"
  Write-Host "Then re-run this script."
  exit 1
}

$visibility = if ($Private) { "--private" } else { "--public" }
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (git remote get-url origin 2>$null)) {
  & $gh repo create $Name $visibility --source=. --remote=origin --push --description "Aegis IDS — ML intrusion detection, XAI, risk, recommendations, attack-defense simulation"
} else {
  git push -u origin main
}

& $gh repo view --web
