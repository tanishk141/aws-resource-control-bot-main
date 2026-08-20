# Script to easily add multiple users to the bot
# Usage: .\add-users.ps1 155604932 987654321 123456789

param(
    [Parameter(Mandatory=$false, ValueFromRemainingArguments=$true)]
    [string[]]$UserIds
)

# Colors
$Green = "Green"
$Blue = "Cyan"
$Yellow = "Yellow"
$Red = "Red"

Write-Host "🤖 Production Control Bot - Add Multiple Users" -ForegroundColor $Blue
Write-Host ""

# Check if user provided any IDs
if ($UserIds.Count -eq 0) {
    Write-Host "Error: No user IDs provided" -ForegroundColor $Red
    Write-Host "Usage: .\add-users.ps1 155604932 987654321 123456789" -ForegroundColor $Yellow
    Write-Host ""
    Write-Host "Get user IDs by:"
    Write-Host "  1. User sends /start to bot"
    Write-Host "  2. Check CloudWatch logs:"
    Write-Host "     aws logs tail TelegramResourceControlBotStack-BotLogGroup11FD2D9F-yB0Q2KfVLm34 --region ap-south-1 --follow"
    Write-Host "  3. Look for: 'Checking authorization for user_id=XXX'"
    exit 1
}

# Join all provided IDs with commas
$UserIdString = $UserIds -join ","

Write-Host "Adding users: $UserIdString" -ForegroundColor $Blue
Write-Host ""

# Read current cdk.json
$CDKFile = "cdk.json"

if (-not (Test-Path $CDKFile)) {
    Write-Host "Error: $CDKFile not found" -ForegroundColor $Red
    exit 1
}

# Backup original file
Copy-Item $CDKFile "$CDKFile.backup"
Write-Host "✓ Backup created: $CDKFile.backup" -ForegroundColor $Green
Write-Host ""

# Read the JSON
$json = Get-Content $CDKFile | ConvertFrom-Json

# Update the allowedUserIds
$json.context.allowedUserIds = $UserIdString

# Write back to file
$json | ConvertTo-Json -Depth 10 | Set-Content $CDKFile

Write-Host "✓ Updated cdc.json with new user IDs" -ForegroundColor $Green
Write-Host ""

# Show what was updated
Write-Host "New configuration:" -ForegroundColor $Blue
$content = Get-Content $CDKFile
$content | Select-String "allowedUserIds"
Write-Host ""

# Ask if user wants to deploy
Write-Host "Do you want to deploy now? (y/n)" -ForegroundColor $Yellow
$response = Read-Host

if ($response -eq "y" -or $response -eq "Y") {
    Write-Host ""
    Write-Host "Deploying..." -ForegroundColor $Blue
    Write-Host ""
    
    npm run deploy
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Deployment successful!" -ForegroundColor $Green
        Write-Host "All users can now use the bot." -ForegroundColor $Green
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "✗ Deployment failed" -ForegroundColor $Red
        Write-Host "To retry, run: npm run deploy" -ForegroundColor $Yellow
        Write-Host ""
    }
} else {
    Write-Host ""
    Write-Host "Skipped deployment." -ForegroundColor $Yellow
    Write-Host "To deploy later, run: npm run deploy" -ForegroundColor $Blue
    Write-Host ""
}

Write-Host "Done!" -ForegroundColor $Green
