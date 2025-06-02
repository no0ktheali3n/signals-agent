# Copy justfile to root if not already present
$justSource = "$PSScriptRoot\..\utils\justfile"
$justDest = "$PSScriptRoot\..\justfile"

if (!(Test-Path $justDest)) {
    Copy-Item $justSource $justDest -Force
    Write-Host "Copied justfile to project root." -ForegroundColor Green
} else {
    Write-Host "justfile already exists in root." -ForegroundColor Gray
}

# Run jumpstarter.ps1 to initialize .gitignore, pyproject.toml, requirements.in, .env.example, and README.md
$jumpstarter = "$PSScriptRoot\jumpstarter.ps1"

if (Test-Path $jumpstarter) {
    Write-Host "Bootstrapping project files with jumpstarter.ps1..." -ForegroundColor Cyan
    powershell -ExecutionPolicy Bypass -File $jumpstarter
} else {
    Write-Host "jumpstarter.ps1 not found - skipping project file generation." -ForegroundColor Yellow
}