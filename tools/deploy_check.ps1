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

Write-Host "Building AI_EDU static site"
Write-Host "  SITE_URL=$env:SITE_URL"
Write-Host "  SUPPORT_EMAIL=$env:SUPPORT_EMAIL"

python build_site.py
python tools/validate_dist.py

Write-Host ""
Write-Host "Deploy-ready dist folder created."
Write-Host "Cloudflare Pages command:"
Write-Host "  wrangler pages deploy dist --project-name=ai-edu-archive"
