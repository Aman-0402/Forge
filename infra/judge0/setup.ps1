# Creates judge0.conf from judge0.conf.example with random secrets.
# Safe to re-run: an existing judge0.conf is never overwritten.
# Prints the API token to copy into backend/.env as JUDGE0_AUTH_TOKEN.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path judge0.conf) {
    Write-Host "judge0.conf already exists; leaving it unchanged."
    $existing = Select-String judge0.conf -Pattern '^AUTHN_TOKEN=(.*)$'
    if ($existing) { Write-Host "JUDGE0_AUTH_TOKEN=$($existing.Matches[0].Groups[1].Value)" }
    exit 0
}

function New-Secret([int]$bytes = 32) {
    $buffer = New-Object byte[] $bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($buffer)
    return ([System.BitConverter]::ToString($buffer) -replace '-', '').ToLower()
}

$token = New-Secret 24
$conf = Get-Content judge0.conf.example -Raw
$conf = $conf -replace '(?m)^REDIS_PASSWORD=.*$', "REDIS_PASSWORD=$(New-Secret)"
$conf = $conf -replace '(?m)^POSTGRES_PASSWORD=.*$', "POSTGRES_PASSWORD=$(New-Secret)"
$conf = $conf -replace '(?m)^SECRET_KEY_BASE=.*$', "SECRET_KEY_BASE=$(New-Secret 64)"
$conf = $conf -replace '(?m)^AUTHN_TOKEN=.*$', "AUTHN_TOKEN=$token"
# Enable waiting for results on single runs; batched submissions stay enabled by default.
$conf = $conf -replace '(?m)^ENABLE_WAIT_RESULT=.*$', "ENABLE_WAIT_RESULT=true"
Set-Content judge0.conf $conf -NoNewline

Write-Host "Created judge0.conf."
Write-Host "Add this to backend/.env:"
Write-Host "JUDGE0_URL=http://127.0.0.1:2358"
Write-Host "JUDGE0_AUTH_TOKEN=$token"
