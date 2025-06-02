# powershell/jumpstarter.ps1
function Get-GitignoreContent {
    return @"
    
#Python
__pycache__/
.uv/
.venv/
.env
*.lock
*.pyc
*.pyo
*.pyd

#OS
.DS_Store
*.sqlite3
*.log
*.db

#IDEs
.idea/
.vscode/
"@ 
}

function Get-PyprojectContent {
    return @"

[project]
name = "my-uv-bootstrap"
version = "0.1.0"
description = "uv environment template for Python projects"
authors = [{ name = "Your Name", email = "you@example.com" }]
requires-python = ">=3.10"

lockfile = "requirements.lock.txt"
"@    
}

function Get-RequirementsContent {
    return @"
requests
python-dotenv
"@
}

function Get-EnvExampleContent {
    return @"

# Example env vars
API_KEY=your-api-key
DEBUG=true
"@
}

function Get-ReadmeContent {
    return @"

# My UV Project

## Setup

1. Create environment (first time only):
    uv venv

2. Install dependencies:
    uv pip install -r requirements.in

3. Lock dependencies:
    uv pip compile requirements.in > requirements.lock.txt

4. Sync (reproducible install):
    uv pip sync requirements.lock.txt
"@
}

$gitignoreContent = Get-GitignoreContent
$pyprojectContent = Get-PyprojectContent
$requirementsContent = Get-RequirementsContent
$envExampleContent = Get-EnvExampleContent
$readmeContent = Get-ReadmeContent

# creates .gitignore, pyproject.toml, requirements.in, .env.example, 
# and README.md in the current directory if they dont already exist
# or appends them if they do exist but are missing the relevant content

#gitignore
if (!(Test-Path ".gitignore")) {
    $gitignoreContent | Set-Content ".gitignore"
    Write-Host "Created .gitignore" -ForegroundColor Green
} elseif(-not (Get-Content .gitignore | Select-String "__pycache__")) {
    "`n$gitignoreContent" | Add-Content ".gitignore"
    Write-Host ".gitignore already exists." -ForegroundColor Gray
} else {
    Write-Host ".gitignore already contains setup info. Skipping." -ForegroundColor Gray
}

#pyproject
if (!(Test-Path "pyproject.toml")) {
    $pyprojectContent | Set-Content "pyproject.toml"
    Write-Host "Created pyproject.toml" -ForegroundColor Green
} elseif(-not (Get-Content pyproject.toml | Select-String "my-uv-bootstrap")) {
    "`n$pyprojectContent" | Add-Content "pyproject.toml"
    Write-Host "pyproject.toml already exists, appended." -ForegroundColor Gray
} else {
    Write-Host "pyproject.toml already contains setup info. Skipping." -ForegroundColor Gray
}

#requirements
if (!(Test-Path "requirements.in")) {
    $requirementsContent | Set-Content "requirements.in"
    Write-Host "Created requirements.in" -ForegroundColor Green
} 
elseif (-not (Get-Content requirements.in | Select-String "requests")) {
    Write-Host "requirements.in already exists, appended." -ForegroundColor Gray
} else {
    Write-Host "requirements.in already contains setup info. Skipping." -ForegroundColor Gray
}

#.env.example
if (!(Test-Path ".env.example")) {
    $envExampleContent | Set-Content ".env.example"
    Write-Host "Created .env.example" -ForegroundColor Green
} elseif (-not (Get-Content .env.example | Select-String "API_KEY")) {
    "`n$envExampleContent" | Add-Content ".env.example"
    Write-Host ".env.example already exists, appended." -ForegroundColor Gray
} else {
    Write-Host ".env.example already contains setup info. Skipping." -ForegroundColor Gray
}

#README.md
if (!(Test-Path "README.md")) {
    $readmeContent | Set-Content "README.md"
    Write-Host "Created README.md" -ForegroundColor Green
}
elseif (-not (Get-Content README.md | Select-String "My UV Project")) {
    "`n$readmeContent" | Add-Content "README.md"
    Write-Host "README.md already exists, appended." -ForegroundColor Yellow
}
else {
    Write-Host "README.md already contains setup info. Skipping." -ForegroundColor Gray
}