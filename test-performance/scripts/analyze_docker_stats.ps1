param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[A-Za-z0-9_-]+$")]
    [string]$RunName
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Find the results directory based on this script's location.
$performanceRoot = Split-Path $PSScriptRoot -Parent
$resultsDir = Join-Path $performanceRoot "results"

# Input: raw monitoring data.
$statsFile = Join-Path $resultsDir "$RunName-docker-stats.txt"

# Output: calculated summary data.
$summaryFile = Join-Path $resultsDir "$RunName-docker-summary.csv"

if (-not (Test-Path -LiteralPath $statsFile)) {
    throw "Docker stats file was not found: $statsFile"
}

# Convert Docker memory text such as 840.7MiB or 1.2GiB into MiB.
function Convert-ToMiB {
    param(
        [Parameter(Mandatory = $true)]
        [string]$MemoryUsage
    )

    # "840.7MiB / 13.5GiB" becomes "840.7MiB".
    $usedMemory = ($MemoryUsage -split "/")[0].Trim()

    if ($usedMemory -notmatch "^([\d.]+)\s*(B|kB|KB|KiB|MB|MiB|GB|GiB)$") {
        throw "Unsupported memory value: $MemoryUsage"
    }

    $number = [double]$Matches[1]
    $unit = $Matches[2]

    switch -CaseSensitive ($unit) {
        "B"   { return $number / 1MB }
        "kB"  { return ($number * 1000) / 1MB }
        "KB"  { return ($number * 1000) / 1MB }
        "KiB" { return $number / 1024 }
        "MB"  { return ($number * 1MB) / 1MB }
        "MiB" { return $number }
        "GB"  { return ($number * 1GB) / 1MB }
        "GiB" { return $number * 1024 }
    }
}

# Read every raw monitoring row and convert text into numbers.
$parsedRows = Import-Csv -LiteralPath $statsFile -Delimiter "|" |
    ForEach-Object {
        [pscustomobject]@{
            Timestamp         = [datetime]$_.timestamp
            Container         = $_.name
            CpuPercent        = [double]($_.cpu.TrimEnd("%"))
            MemoryMiB         = Convert-ToMiB -MemoryUsage $_.mem_usage
            MemoryPercent     = [double]($_.mem_percent.TrimEnd("%"))
            Pids              = [int]$_.pids
        }
    }

if (-not $parsedRows) {
    throw "The Docker stats file contains no data rows."
}

# By default, analyze every monitoring row.
$analysisRows = @($parsedRows)

# If a matching JMeter log exists, use only the actual test time window.
$jmeterLog = Join-Path $resultsDir "$RunName.log"

if (Test-Path -LiteralPath $jmeterLog) {
    $logLines = Get-Content -LiteralPath $jmeterLog

    $startLine = $logLines |
        Where-Object { $_ -match "Running the test!" } |
        Select-Object -First 1

    $endLine = $logLines |
        Where-Object { $_ -match "Summariser: summary =" } |
        Select-Object -Last 1

    if ($startLine -and $endLine) {
        $dateFormat = "yyyy-MM-dd HH:mm:ss,fff"
        $culture = [System.Globalization.CultureInfo]::InvariantCulture

        $testStart = [datetime]::ParseExact(
            $startLine.Substring(0, 23),
            $dateFormat,
            $culture
        )

        $testEnd = [datetime]::ParseExact(
            $endLine.Substring(0, 23),
            $dateFormat,
            $culture
        )

        $analysisRows = @(
            $parsedRows |
                Where-Object {
                    $_.Timestamp -ge $testStart -and
                    $_.Timestamp -le $testEnd
                }
        )

        if (-not $analysisRows) {
            throw "No Docker monitoring data was found inside the JMeter test window."
        }

        Write-Host "JMeter test window was detected."
        Write-Host "Test start: $testStart"
        Write-Host "Test end  : $testEnd"
    }
}
else {
    Write-Host "Matching JMeter log was not found."
    Write-Host "All Docker monitoring rows will be analyzed."
}

# Group rows by container and calculate summary values.
$summary = $analysisRows |
    Group-Object Container |
    ForEach-Object {
        $orderedRows = @($_.Group | Sort-Object Timestamp)

        $cpuResult = $orderedRows |
            Measure-Object -Property CpuPercent -Average -Maximum

        $memoryResult = $orderedRows |
            Measure-Object -Property MemoryMiB -Minimum -Maximum -Average

        $pidsResult = $orderedRows |
            Measure-Object -Property Pids -Maximum

        [pscustomobject]@{
            Container        = $_.Name
            Samples          = $orderedRows.Count
            AverageCpuPct    = [math]::Round($cpuResult.Average, 2)
            MaximumCpuPct    = [math]::Round($cpuResult.Maximum, 2)
            FirstMemoryMiB   = [math]::Round($orderedRows[0].MemoryMiB, 2)
            LastMemoryMiB    = [math]::Round($orderedRows[-1].MemoryMiB, 2)
            MinimumMemoryMiB = [math]::Round($memoryResult.Minimum, 2)
            MaximumMemoryMiB = [math]::Round($memoryResult.Maximum, 2)
            AverageMemoryMiB = [math]::Round($memoryResult.Average, 2)
            MaximumPids      = $pidsResult.Maximum
        }
    }

# Display the summary and save it as a CSV file.
$summary | Format-List
$summary | Export-Csv -LiteralPath $summaryFile -NoTypeInformation -Encoding UTF8

Write-Host "Docker stats analysis completed successfully."
Write-Host "Summary file: $summaryFile"