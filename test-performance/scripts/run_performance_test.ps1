param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 5000)]
    [int]$Users,

    [ValidateRange(1, 3600)]
    [int]$RampUp = 20,

    [ValidateRange(1, 86400)]
    [int]$Duration = 120,

    [ValidateRange(0, 60000)]
    [int]$Delay = 500,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[A-Za-z0-9_-]+$")]
    [string]$RunName,

    [ValidateRange(1, 60)]
    [int]$MonitorInterval = 2,

    [string]$JMeterHome = $env:JMETER_HOME
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Locate the three existing scripts.
$runJMeterScript = Join-Path $PSScriptRoot "run_jmeter.ps1"
$monitorScript = Join-Path $PSScriptRoot "monitor_docker.ps1"
$analyzeScript = Join-Path $PSScriptRoot "analyze_docker_stats.ps1"

$performanceRoot = Split-Path $PSScriptRoot -Parent
$resultsDir = Join-Path $performanceRoot "results"

foreach ($script in @($runJMeterScript, $monitorScript, $analyzeScript)) {
    if (-not (Test-Path -LiteralPath $script)) {
        throw "Required script was not found: $script"
    }
}

New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null

# Check every output before starting, so old evidence is not overwritten.
$expectedOutputs = @(
    (Join-Path $resultsDir "$RunName.jtl"),
    (Join-Path $resultsDir "$RunName.log"),
    (Join-Path $resultsDir "$RunName-report"),
    (Join-Path $resultsDir "$RunName-docker-stats.txt"),
    (Join-Path $resultsDir "$RunName-docker-summary.csv"),
    (Join-Path $resultsDir "$RunName-monitor-output.log"),
    (Join-Path $resultsDir "$RunName-monitor-error.log")
)

foreach ($output in $expectedOutputs) {
    if (Test-Path -LiteralPath $output) {
        throw "RunName already exists. Use a new RunName: $RunName"
    }
}

$monitorOutput = Join-Path $resultsDir "$RunName-monitor-output.log"
$monitorError = Join-Path $resultsDir "$RunName-monitor-error.log"

$monitorArguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$monitorScript`"",
    "-RunName", $RunName,
    "-IntervalSeconds", $MonitorInterval,
    "-SampleCount", "0"
)

Write-Host "Starting complete performance test..."
Write-Host "Users          : $Users"
Write-Host "Ramp-up        : $RampUp seconds"
Write-Host "Duration       : $Duration seconds"
Write-Host "Request delay  : $Delay milliseconds"
Write-Host "Monitor interval: $MonitorInterval seconds"
Write-Host "Run name       : $RunName"

# Start Docker monitoring in a hidden background PowerShell process.
$monitorProcess = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList $monitorArguments `
    -RedirectStandardOutput $monitorOutput `
    -RedirectStandardError $monitorError `
    -WindowStyle Hidden `
    -PassThru

try {
    # Give the monitor enough time to save its first resource sample.
    Start-Sleep -Seconds 3

    $monitorProcess.Refresh()

    if ($monitorProcess.HasExited) {
        throw "Docker monitoring stopped unexpectedly. Check: $monitorError"
    }

    # Run the JMeter test in the current terminal.
    & $runJMeterScript `
        -Users $Users `
        -RampUp $RampUp `
        -Duration $Duration `
        -Delay $Delay `
        -RunName $RunName `
        -JMeterHome $JMeterHome
}
finally {
    # Always stop the monitor, even if JMeter fails.
    Start-Sleep -Seconds 1
    $monitorProcess.Refresh()

    if (-not $monitorProcess.HasExited) {
        Stop-Process -Id $monitorProcess.Id -Force
        $monitorProcess.WaitForExit()
    }

    Write-Host "Docker monitoring process has been stopped."
}

# Analyze only the Docker samples inside the JMeter test window.
& $analyzeScript -RunName $RunName

Write-Host ""
Write-Host "Complete performance test finished successfully." `
    -ForegroundColor Green
Write-Host "Run name: $RunName"
Write-Host "Results : $resultsDir"