param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$GoogleClientId,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$AllowedEmails,

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$SessionSecret,

    [switch]$SkipDeploy
)

$ErrorActionPreference = 'Stop'

function Set-GitHubSecret {
    param(
        [Parameter(Mandatory = $true)] [string]$Name,
        [Parameter(Mandatory = $true)] [string]$Value
    )

    $Value | gh secret set $Name --body-file -
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'GitHub CLI is required. Install gh and run gh auth login first.'
}

gh auth status | Out-Null

$emailList = $AllowedEmails.Split(',') | ForEach-Object { $_.Trim().ToLowerInvariant() } | Where-Object { $_ }
if ($emailList.Count -eq 0) {
    throw 'AllowedEmails must contain at least one email address.'
}

if (-not $GoogleClientId.EndsWith('.apps.googleusercontent.com')) {
    Write-Warning 'GoogleClientId does not end with .apps.googleusercontent.com. Verify this is a Web OAuth 2.0 Client ID.'
}

if (-not $SessionSecret) {
    $bytes = [byte[]]::new(32)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $SessionSecret = -join ($bytes | ForEach-Object { $_.ToString('x2') })
}

$normalizedAllowedEmails = ($emailList -join ',')

Set-GitHubSecret -Name 'GOOGLE_CLIENT_ID' -Value $GoogleClientId.Trim()
Set-GitHubSecret -Name 'ALLOWED_EMAILS' -Value $normalizedAllowedEmails
Set-GitHubSecret -Name 'SESSION_SECRET' -Value $SessionSecret

Write-Host 'Configured GitHub Secrets: GOOGLE_CLIENT_ID, ALLOWED_EMAILS, SESSION_SECRET'
Write-Host "Allowed emails: $normalizedAllowedEmails"

if (-not $SkipDeploy) {
    gh workflow run main_stock.yml --ref main
    Write-Host 'Triggered GitHub Actions workflow main_stock.yml on main.'
}
