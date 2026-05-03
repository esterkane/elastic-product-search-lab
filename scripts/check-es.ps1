$ErrorActionPreference = "Stop"

$envPath = Join-Path (Resolve-Path "$PSScriptRoot\..") ".env"
if (Test-Path $envPath) {
  Get-Content $envPath | ForEach-Object {
    if ($_ -match "^\s*#" -or $_ -notmatch "=") {
      return
    }
    $name, $value = $_ -split "=", 2
    if ($name -and -not [Environment]::GetEnvironmentVariable($name)) {
      [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
    }
  }
}

$url = $env:ELASTICSEARCH_URL
if (-not $url) {
  $url = "http://localhost:9200"
}

$authorizationHeader = $null
if (($env:ELASTICSEARCH_USE_AUTH -match "^(1|true|yes)$") -and $env:ELASTICSEARCH_USERNAME -and $env:ELASTICSEARCH_PASSWORD) {
  $authBytes = [System.Text.Encoding]::ASCII.GetBytes("$($env:ELASTICSEARCH_USERNAME):$($env:ELASTICSEARCH_PASSWORD)")
  $authorizationHeader = "Basic $([Convert]::ToBase64String($authBytes))"
}

try {
  $request = @{
    Method = "Get"
    TimeoutSec = 5
  }
  if ($authorizationHeader) {
    $request.Headers = @{ Authorization = $authorizationHeader }
  }

  $info = Invoke-RestMethod -Uri $url @request
  $health = Invoke-RestMethod -Uri "$url/_cluster/health" @request

  Write-Host "Elasticsearch is reachable at $url"
  Write-Host "cluster_name: $($info.cluster_name)"
  Write-Host "version: $($info.version.number)"
  Write-Host "status: $($health.status)"
}
catch {
  Write-Error "Elasticsearch is not reachable at $url. Start it with scripts/dev-up.ps1 or inspect Docker logs. $($_.Exception.Message)"
  exit 1
}
