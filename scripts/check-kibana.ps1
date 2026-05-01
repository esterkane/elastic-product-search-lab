$ErrorActionPreference = "Stop"

$url = $env:KIBANA_URL
if (-not $url) {
  $url = "http://localhost:5601"
}

try {
  $status = Invoke-RestMethod -Uri "$url/api/status" -Method Get -TimeoutSec 10
  $level = $status.status.overall.level

  if ($level -ne "available") {
    Write-Error "Kibana is reachable at $url but status is '$level'. Wait a moment and retry."
    exit 1
  }

  Write-Host "Kibana is reachable at $url"
  Write-Host "status: $level"
}
catch {
  Write-Error "Kibana is not reachable at $url. Start it with scripts/dev-up.ps1 or inspect Docker logs. $($_.Exception.Message)"
  exit 1
}