# Install mda-cli and ensure `mda` is on the user PATH (no admin required).
# Usage: pwsh -File scripts\install-global.ps1
#
# Optional: set MDA_PYTHON to a specific python.exe before running.

$ErrorActionPreference = 'Stop'

function Get-MdaPythonExecutable {
    if ($env:MDA_PYTHON) {
        $explicit = $env:MDA_PYTHON.Trim().Trim('"')
        if (Test-Path $explicit) {
            return (Resolve-Path $explicit).Path
        }
        throw "MDA_PYTHON is set but not found: $explicit"
    }

    $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $candidates = [System.Collections.Generic.List[string]]::new()

    function Add-Candidate([string]$Path) {
        if ([string]::IsNullOrWhiteSpace($Path)) { return }
        try {
            $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
        }
        catch {
            return
        }
        if ($seen.Add($resolved)) {
            [void]$candidates.Add($resolved)
        }
    }

    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        foreach ($ver in @('-3.13', '-3.12', '-3.11', '-3.10')) {
            try {
                $out = & py $ver -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $out) {
                    Add-Candidate ($out.Trim())
                }
            }
            catch { }
        }
    }

    foreach ($name in @('python3', 'python')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { Add-Candidate $cmd.Source }
    }

    $localApp = [Environment]::GetFolderPath('LocalApplicationData')
    if ($localApp) {
        Get-ChildItem -Path (Join-Path $localApp 'Programs\Python') -Filter 'python.exe' -Recurse -ErrorAction SilentlyContinue |
            ForEach-Object { Add-Candidate $_.FullName }
    }

    foreach ($candidate in $candidates) {
        try {
            $version = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($LASTEXITCODE -ne 0) { continue }
            $parts = $version.Trim().Split('.')
            if ($parts.Count -ge 2) {
                $major = [int]$parts[0]
                $minor = [int]$parts[1]
                if ($major -eq 3 -and $minor -ge 10) {
                    return $candidate
                }
            }
        }
        catch { }
    }

    throw @(
        'Python 3.10+ not found.'
        'Install Python, set MDA_PYTHON to python.exe, or ensure `py -3.12` / `python` works.'
    ) -join ' '
}

function Stop-MdaInstallProcesses {
    $stopped = $false
    foreach ($procName in @('mda', 'mda-cli', 'mda-tui')) {
        $procs = Get-Process -Name $procName -ErrorAction SilentlyContinue
        if ($procs) {
            $procs | Stop-Process -Force -ErrorAction SilentlyContinue
            $stopped = $true
        }
    }
    if ($stopped) {
        Write-Host 'Stopped running mda process(es) so pip can replace mda.exe.'
        Start-Sleep -Milliseconds 750
    }
}

$Python = Get-MdaPythonExecutable
Write-Host "Using Python: $Python"

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot 'pyproject.toml'))) {
    throw "pyproject.toml not found under $RepoRoot"
}

$ScriptsDir = Join-Path (Split-Path -Parent $Python) 'Scripts'

Stop-MdaInstallProcesses

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
