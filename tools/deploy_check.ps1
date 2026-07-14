param(
  [string]$SiteUrl = $env:SITE_URL,
  [string]$SupportEmail = $env:SUPPORT_EMAIL
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($SiteUrl)) {
  $SiteUrl = "https://ai-edu-archive.pages.dev"
}

if ([string]::IsNullOrWhiteSpace($SupportEmail)) {
  $hostName = $SiteUrl -replace '^https?://', ''
  $hostName = $hostName.TrimEnd('/')
  $SupportEmail = "hello@$hostName"
}

$env:SITE_URL = $SiteUrl
$env:SUPPORT_EMAIL = $SupportEmail

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Command,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
  )

  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
  }
}

Write-Host "Building AI_EDU static site"
Write-Host "  SITE_URL=$env:SITE_URL"
Write-Host "  SUPPORT_EMAIL=$env:SUPPORT_EMAIL"

Invoke-Checked python tools/site_contract.py --check
Invoke-Checked python tools/audit_editorial_voice.py --lang en --strict
Invoke-Checked python tools/audit_editorial_voice.py --lang ko --strict
Invoke-Checked python tools/audit_content_depth.py --lang en --strict
Invoke-Checked python tools/audit_content_depth.py --lang ko --strict
Invoke-Checked python build_site.py
Invoke-Checked python tools/validate_dist.py

Write-Host ""
Write-Host "Deploy-ready dist folder created."
Write-Host "Cloudflare Pages command:"
Write-Host "  wrangler pages deploy dist --project-name=ai-edu-archive"
