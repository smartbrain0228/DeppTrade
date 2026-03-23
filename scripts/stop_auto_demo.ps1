$targetPorts = @(8002, 8003)
$stoppedAny = $false

foreach ($port in $targetPorts) {
  $lines = netstat -ano -p tcp | Select-String -Pattern "127.0.0.1:$port\s+.*LISTENING\s+(\d+)$"

  if (-not $lines) {
    continue
  }

  foreach ($line in $lines) {
    if ($line.Matches.Count -eq 0) {
      continue
    }

    $pid = [int]$line.Matches[0].Groups[1].Value

    try {
      taskkill /PID $pid /F | Out-Null
      Write-Output "Stopped auto-demo process $pid on port $port."
      $stoppedAny = $true
    } catch {
      Write-Output ("Failed to stop process {0} on port {1}: {2}" -f $pid, $port, $_.Exception.Message)
    }
  }
}

if (-not $stoppedAny) {
  Write-Output "No auto-demo process found on ports 8002 or 8003."
}
