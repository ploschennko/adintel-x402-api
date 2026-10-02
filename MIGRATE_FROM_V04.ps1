$ErrorActionPreference = 'Stop'
$parent = Split-Path -Parent $PSScriptRoot
$src = Join-Path $parent 'adintel_x402_mvp_v0_4'

if (-not (Test-Path $src)) {
    Write-Host "Could not find sibling folder: $src" -ForegroundColor Yellow
    Write-Host "Copy .env, .buyer.env and data\adintel.sqlite3 manually from your v0.4 folder." -ForegroundColor Yellow
    exit 1
}

foreach ($name in @('.env', '.buyer.env')) {
    $from = Join-Path $src $name
    if (Test-Path $from) {
        Copy-Item $from (Join-Path $PSScriptRoot $name) -Force
        Write-Host "Copied $name" -ForegroundColor Green
    } else {
        Write-Host "Skipped $name (not found)" -ForegroundColor DarkYellow
    }
}

$dataDir = Join-Path $PSScriptRoot 'data'
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
$dbFrom = Join-Path $src 'data\adintel.sqlite3'
if (Test-Path $dbFrom) {
    Copy-Item $dbFrom (Join-Path $dataDir 'adintel.sqlite3') -Force
    Write-Host "Copied data\adintel.sqlite3" -ForegroundColor Green
} else {
    Write-Host "Skipped database (not found)" -ForegroundColor DarkYellow
}

Write-Host "Migration files copied. You can now run .\RUN_WINDOWS.bat" -ForegroundColor Cyan
