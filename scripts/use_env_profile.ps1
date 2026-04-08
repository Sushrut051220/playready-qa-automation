param(
    [ValidateSet('openai', 'ollama', 'enterprise')]
    [string]$Profile = 'openai',
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$profileMap = @{
    openai = Join-Path $repoRoot 'config\env\.env.openai.example'
    ollama = Join-Path $repoRoot 'config\env\.env.ollama.example'
    enterprise = Join-Path $repoRoot 'enterprise\config\.env.enterprise.example'
}

$sourcePath = $profileMap[$Profile]
$targetPath = Join-Path $repoRoot '.env'

if (-not (Test-Path $sourcePath)) {
    throw "Profile file not found: $sourcePath"
}

Write-Host "Profile : $Profile"
Write-Host "Source  : $sourcePath"
Write-Host "Target  : $targetPath"

if ($DryRun) {
    Write-Host 'Dry run only. No file copied.'
    exit 0
}

Copy-Item -Path $sourcePath -Destination $targetPath -Force
Write-Host 'Copied the selected profile to .env.'
Write-Host 'Next: open .env and update only the placeholder values before running tests.'
