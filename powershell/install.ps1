# Detect user profile path
$profilePath = "$HOME\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"
$profileDir = Split-Path -Parent $profilePath

# Detect PowerShell version
$psMajor = $PSVersionTable.PSVersion.Major

# Assign appropriate script based on PowerShell version
if ($psMajor -ge 7) {
    $autoenvScript = "$PSScriptRoot\autoenv_ps7.ps1"
    Write-Host "PowerShell 7+ detected, using enhanced autoenv" -ForegroundColor Cyan
} else {
    $autoenvScript = "$PSScriptRoot\autoenv_ps5.ps1"
    Write-Host "PowerShell 5.1 or below detected, using minimal autoenv" -ForegroundColor Yellow
}

# Ensure profile directory exists
if (!(Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}

# Ensure profile file exists
if (!(Test-Path $profilePath)) {
    New-Item -ItemType File -Path $profilePath -Force | Out-Null
}

# Append script reference if not already present
$profileContent = Get-Content $profilePath -Raw
if ($profileContent -notmatch [regex]::Escape($autoenvScript)) {
    Add-Content $profilePath "`n. '$autoenvScript'"
    Write-Host "Added autoenv script to PowerShell profile." -ForegroundColor Green
} else {
    Write-Host "Autoenv script already present in profile." -ForegroundColor Gray
}

# calls setup.ps1 to copy utils\justfile to project root if not already present
$setupScript = "$PSScriptRoot\setup.ps1"
if (Test-Path $setupScript) {
    & $setupScript
} else {
    Write-Host "setup.ps1 not found - skipping project bootstrap." -ForegroundColor Yellow
}