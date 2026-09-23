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

    [string]$JMeterHome = $env:JMETER_HOME
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve JMeter executable.
if ([string]::IsNullOrWhiteSpace($JMeterHome)) {
    $jmeterCommand = Get-Command "jmeter.bat" -ErrorAction SilentlyContinue

    if (-not $jmeterCommand) {
        throw "JMeter was not found. Set JMETER_HOME or add JMeter bin to PATH."
    }

    $jmeterBat = $jmeterCommand.Source
}
else {
    $jmeterBat = Join-Path $JMeterHome "bin\jmeter.bat"
}

if (-not (Test-Path -LiteralPath $jmeterBat)) {
    throw "JMeter executable was not found: $jmeterBat"
}

# Resolve project paths relative to this script.
$performanceRoot = Split-Path $PSScriptRoot -Parent
$testPlan = Join-Path $performanceRoot "jmeter\litemall_home_stress.jmx"
$resultsDir = Join-Path $performanceRoot "results"

if (-not (Test-Path -LiteralPath $testPlan)) {
    throw "JMeter test plan was not found: $testPlan"
}

New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null

$jtlFile = Join-Path $resultsDir "$RunName.jtl"
$logFile = Join-Path $resultsDir "$RunName.log"
$reportDir = Join-Path $resultsDir "$RunName-report"

# Protect existing test evidence from accidental overwrite.
if (
    (Test-Path -LiteralPath $jtlFile) -or
    (Test-Path -LiteralPath $logFile) -or
    (Test-Path -LiteralPath $reportDir)
) {
    throw "RunName already exists. Use a new RunName: $RunName"
}

$jmeterArgs = @(
    "-n"
    "-t", $testPlan
    "-Jusers=$Users"
    "-Jrampup=$RampUp"
    "-Jduration=$Duration"
    "-Jdelay=$Delay"
    "-l", $jtlFile
    "-j", $logFile
    "-e"
    "-o", $reportDir
)

Write-Host "Starting JMeter test..."
Write-Host "Users   : $Users"
Write-Host "Ramp-up : $RampUp seconds"
Write-Host "Duration: $Duration seconds"
Write-Host "Delay   : $Delay milliseconds"
Write-Host "Run name: $RunName"

& $jmeterBat @jmeterArgs

if ($LASTEXITCODE -ne 0) {
    throw "JMeter failed with exit code $LASTEXITCODE. Check: $logFile"
}

Write-Host "JMeter test completed successfully." -ForegroundColor Green
Write-Host "JTL report : $jtlFile"
Write-Host "JMeter log : $logFile"
Write-Host "HTML report: $reportDir"