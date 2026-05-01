$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (-not $env:ELASTIC_VERSION) {
  $env:ELASTIC_VERSION = "9.3.0"
}

Write-Host "Starting Elasticsearch $env:ELASTIC_VERSION..."
docker compose up -d elasticsearch

Write-Host "Waiting for Elasticsearch to answer on http://localhost:9200..."
& (Join-Path $PSScriptRoot "check-es.ps1")
