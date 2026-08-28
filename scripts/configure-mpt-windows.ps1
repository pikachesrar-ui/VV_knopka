$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envPath = Join-Path $repoRoot ".env"
$mptConfig = Join-Path $repoRoot "MoneyPrinterTurbo\config.toml"

if (-not (Test-Path $envPath)) {
    throw "Missing VV_knopka/.env"
}
if (-not (Test-Path $mptConfig)) {
    throw "Missing MoneyPrinterTurbo/config.toml. Run setup-mpt-windows.ps1 first."
}

$pexelsKey = ""
foreach ($line in Get-Content $envPath) {
    if ($line -match '^\s*PEXELS_API_KEY\s*=\s*(.+?)\s*$') {
        $pexelsKey = $Matches[1].Trim().Trim('"').Trim("'")
        break
    }
}

if (-not $pexelsKey) {
    throw "PEXELS_API_KEY is empty in VV_knopka/.env. Create a free Pexels API key and add it first."
}

# Escape only what is required for a TOML basic string.
$escapedKey = $pexelsKey.Replace('\', '\\').Replace('"', '\"')
$content = Get-Content $mptConfig -Raw
$content = [regex]::Replace($content, '(?m)^listen_host\s*=\s*".*"\s*$', 'listen_host = "127.0.0.1"', 1)
$content = [regex]::Replace($content, '(?m)^listen_port\s*=\s*\d+\s*$', 'listen_port = 8080', 1)
$content = [regex]::Replace($content, '(?m)^video_source\s*=\s*".*"\s*$', 'video_source = "pexels"', 1)
$content = [regex]::Replace($content, '(?m)^pexels_api_keys\s*=\s*\[.*\]\s*$', "pexels_api_keys = [`"$escapedKey`"]", 1)
$content = [regex]::Replace($content, '(?m)^subtitle_provider\s*=\s*".*"\s*$', 'subtitle_provider = "edge"', 1)
$content = [regex]::Replace($content, '(?m)^upload_post_auto_upload\s*=\s*(true|false)\s*$', 'upload_post_auto_upload = false', 1)
$content = [regex]::Replace($content, '(?m)^upload_post_enabled\s*=\s*(true|false)\s*$', 'upload_post_enabled = false', 1)

Set-Content -Path $mptConfig -Value $content -Encoding UTF8

Write-Host "MoneyPrinterTurbo configured:"
Write-Host "  host: 127.0.0.1"
Write-Host "  port: 8080"
Write-Host "  footage: Pexels"
Write-Host "  subtitles: Edge timestamps"
Write-Host "  cross-posting: disabled"
Write-Host "  Pexels key: configured (secret not displayed)"
