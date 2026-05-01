$ErrorActionPreference = "Stop"

$url = $env:ELASTICSEARCH_URL
if (-not $url) {
  $url = "http://localhost:9200"
}

try {
  $info = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 5
  $health = Invoke-RestMethod -Uri "$url/_cluster/health" -Method Get -TimeoutSec 5

  Write-Host "Elasticsearch is reachable at $url"
  Write-Host "cluster_name: $($info.cluster_name)"
  Write-Host "version: $($info.version.number)"
  Write-Host "status: $($health.status)"
}
catch {
  Write-Error "Elasticsearch is not reachable at $url. Start it with scripts/dev-up.ps1 or inspect Docker logs. $($_.Exception.Message)"
  exit 1
}
