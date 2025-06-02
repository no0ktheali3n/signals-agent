# automatially activates venv upon directory change if detected (PowerShell 7.1+ ONLY)
function Enable-VenvAutoActivate {
    $currentPath = Get-Location
    $venvPaths = @(
        "$currentPath\.venv\Scripts\Activate.ps1",
        "$currentPath\.uv\Scripts\Activate.ps1"
    )

    foreach ($path in $venvPaths) {
        if (Test-Path $path) {
            Write-Host "Auto-activating: $path" -ForegroundColor Green
            & $path
            return
        }
    }
}

#hook checks for idle after cd and automatically activates venv if detected
Register-EngineEvent PowerShell.OnIdle -SupportEvent -Action {
    if (-not $global:lastLocation) {
        $global:lastLocation = Get-Location
    }

    $newLocation = Get-Location
    if ($newLocation.Path -ne $global:lastLocation.Path) {
        $global:lastLocation = $newLocation
        Enable-VenvAutoActivate
    }
} | Out-Null