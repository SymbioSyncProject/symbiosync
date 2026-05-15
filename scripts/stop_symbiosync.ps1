param(
    [int]$Port = 8080
)

$ErrorActionPreference = 'Continue'

Write-Host "Best-effort device stop on port $Port..."
try {
    Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$Port/api/stop" -TimeoutSec 3 | Out-Null
    Write-Host 'Stop request sent.'
} catch {
    Write-Host "Stop request skipped/failed: $($_.Exception.Message)"
}

$processes = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine -match '(?i)(^|\\)(py|python)(\.exe)?(\s|$)' -and
    $_.CommandLine -match '(?i)symbiosync'
}

if ($Port -eq 8080) {
    $processes = $processes | Where-Object {
        $_.CommandLine -notmatch '--port(\s+|=)\d+' -or
        $_.CommandLine -match '--port(\s+|=)8080(\s|$)'
    }
} else {
    $portPattern = "--port(\s+|=)$Port(\s|$)"
    $processes = $processes | Where-Object { $_.CommandLine -match $portPattern }
}

if (-not $processes) {
    Write-Host 'No matching SymbioSync Python process found.'
    exit 0
}

foreach ($process in $processes) {
    Write-Host "Stopping PID $($process.ProcessId): $($process.CommandLine)"
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Host 'Done.'
