$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (-not $env:ELASTIC_VERSION) {
  $env:ELASTIC_VERSION = "9.3.0"
}

Write-Host "Starting Elasticsearch and Kibana $env:ELASTIC_VERSION..."
docker compose up -d elasticsearch kibana

Write-Host "Waiting for Elasticsearch to answer on http://localhost:9200..."
& (Join-Path $PSScriptRoot "check-es.ps1")

Write-Host "Waiting for Kibana to answer on http://localhost:5601..."
& (Join-Path $PSScriptRoot "check-kibana.ps1")
