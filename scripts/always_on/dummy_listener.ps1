param([int]$Port = 18789)

$ErrorActionPreference = 'Stop'

$l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
$l.Start()
Write-Output "dummy listening on 127.0.0.1:$Port"
try {
  Start-Sleep -Seconds 120
} finally {
  $l.Stop()
}
