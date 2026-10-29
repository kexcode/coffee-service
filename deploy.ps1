param(
    [string]$CommitMessage = ""
)

$ErrorActionPreference = "Stop"

$SshKey = $env:ORACLE_SSH_KEY
$ServerHost = $env:COFFEE_SERVER_HOST

# Automatically extract SSH connection parameters from local gitignored SERVER_INFRASTRUCTURE.md if not set in env
if ((-not $SshKey -or -not $ServerHost) -and (Test-Path "$PSScriptRoot\SERVER_INFRASTRUCTURE.md")) {
    $InfraContent = Get-Content "$PSScriptRoot\SERVER_INFRASTRUCTURE.md" -Raw
    if (-not $SshKey -and $InfraContent -match 'ssh -i "([^"]+)"\s+(\S+@\S+)') {
        $SshKey = $Matches[1]
        if (-not $ServerHost) {
            $ServerHost = $Matches[2]
        }
    }
}

if (-not $SshKey -or -not $ServerHost) {
    throw "SSH connection details not found. Set `$env:ORACLE_SSH_KEY and `$env:COFFEE_SERVER_HOST or keep SERVER_INFRASTRUCTURE.md in project root."
}

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "Office Coffee Fund - Remote CI/CD Trigger" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

if ($CommitMessage -ne "") {
    Write-Host "`nStaging and committing local changes..." -ForegroundColor Yellow
    git add -A
    git commit -m "$CommitMessage"
}

Write-Host "`nPushing branch 'main' to GitHub..." -ForegroundColor Yellow
git push origin main

Write-Host "`nUpdating scripts on server and triggering CI/CD pipeline..." -ForegroundColor Yellow
ssh -i "$SshKey" $ServerHost "cd ~/coffee-service && git fetch origin main && git reset --hard origin/main && sed -i 's/\r$//' deploy/*.sh && chmod +x deploy/*.sh && bash deploy/deploy.sh"
