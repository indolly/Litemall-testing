param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[A-Za-z0-9_-]+$")]
    [string]$RunName,

    [ValidateRange(1, 60)]
    [int]$IntervalSeconds = 2,

    [ValidateRange(0, 100000)]
    [int]$SampleCount = 0,

    [string[]]$Containers = @("litemall", "mysql")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    throw "Docker command was not found."
}

$performanceRoot = Split-Path $PSScriptRoot -Parent
$resultsDir = Join-Path $performanceRoot "results"
$statsFile = Join-Path $resultsDir "$RunName-docker-stats.txt"

New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null

if (Test-Path -LiteralPath $statsFile) {
    throw "Monitor result already exists. Use a new RunName: $RunName"
}

"timestamp|name|cpu|mem_usage|mem_percent|net_io|block_io|pids" |
    Set-Content -Path $statsFile -Encoding utf8

Write-Host "Starting Docker monitoring..."
Write-Host "Containers : $($Containers -join ', ')"
Write-Host "Interval   : $IntervalSeconds seconds"
Write-Host "Output file: $statsFile"

$completedSamples = 0

try {
    while ($SampleCount -eq 0 -or $completedSamples -lt $SampleCount) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

        $dockerRows = & docker stats `
            --no-stream `
            --format "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}|{{.NetIO}}|{{.BlockIO}}|{{.PIDs}}" `
            $Containers

        if ($LASTEXITCODE -ne 0) {
            throw "docker stats failed with exit code $LASTEXITCODE."
        }

        foreach ($row in $dockerRows) {
            $line = "$timestamp|$row"
            Write-Host $line
            Add-Content -Path $statsFile -Value $line -Encoding utf8
        }

        $completedSamples++

        if ($SampleCount -eq 0 -or $completedSamples -lt $SampleCount) {
            Start-Sleep -Seconds $IntervalSeconds
        }
    }
}
finally {
    Write-Host "Docker monitoring stopped."
    Write-Host "Output file: $statsFile"
}