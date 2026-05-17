# Install mda-cli and ensure `mda` is on the user PATH (no admin required).
# Usage: pwsh -File scripts\install-global.ps1

$ErrorActionPreference = 'Stop'

$Python = 'C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe'
if (-not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction SilentlyContinue)?.Source
    if (-not $Python) { throw 'Python not found. Set $Python at the top of this script or install Python 3.10+.' }
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot 'pyproject.toml'))) {
    throw "pyproject.toml not found under $RepoRoot"
}

$ScriptsDir = Join-Path (Split-Path -Parent $Python) 'Scripts'

Write-Host "Installing mda-cli from $RepoRoot ..."
& $Python -m pip install -e $RepoRoot
if ($LASTEXITCODE -ne 0) { throw "pip install failed (exit $LASTEXITCODE)" }

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$normScripts = $ScriptsDir.TrimEnd('\')
$alreadyOnPath = ($userPath -split ';' | ForEach-Object { $_.TrimEnd('\') }) -contains $normScripts

if (-not $alreadyOnPath) {
    $newPath = if ([string]::IsNullOrWhiteSpace($userPath)) { $normScripts } else { "$userPath;$normScripts" }
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    $env:Path = if ($env:Path -notlike "*$normScripts*") { "$env:Path;$normScripts" } else { $env:Path }
    Write-Host "Added to user PATH: $normScripts"
    Write-Host 'Open a new terminal (or restart Cursor) so PATH changes apply everywhere.'
}
else {
    Write-Host "User PATH already contains: $normScripts"
}

Write-Host ''
Write-Host 'Verification:'
& where.exe mda
& (Join-Path $ScriptsDir 'mda.exe') --version
& (Join-Path $ScriptsDir 'mda.exe') --check
