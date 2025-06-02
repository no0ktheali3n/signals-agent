# Should be manually triggered using Enable-VenvAutoActivate after running install.ps1 (PowerShell 5.1 CLI) in project root, use instead of venv/Scripts/Activate
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
        } else {
            Write-Host "No virtual environment found at: $path" -ForegroundColor Red
        }
    }
}
