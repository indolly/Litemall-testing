param(
    [switch]$OpenReport
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# $PSScriptRoot 是当前脚本所在的 test-automation 目录
$ProjectRoot = Split-Path -Parent $PSScriptRoot

$ResultsDir = Join-Path $PSScriptRoot "allure-results"
$ReportDir = Join-Path $PSScriptRoot "allure-report"

# 检查运行测试和生成报告所需的命令
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "没有找到 Python，请检查 Python 是否已加入 PATH。"
}

if (-not (Get-Command allure -ErrorAction SilentlyContinue)) {
    throw "没有找到 Allure，请检查 Allure 是否已安装并加入 PATH。"
}

Push-Location $ProjectRoot

try {
    Write-Host "开始执行 Litemall 接口自动化测试..." `
        -ForegroundColor Cyan

    # 执行全部测试，并在执行前清理旧的Allure原始数据
    python -m pytest `
        "--alluredir=$ResultsDir" `
        --clean-alluredir

    $PytestExitCode = $LASTEXITCODE

    Write-Host "开始生成 Allure HTML 报告..." `
        -ForegroundColor Cyan

    # 即使用例失败，也生成报告，方便查看失败原因
    allure generate $ResultsDir `
        -o $ReportDir `
        --clean

    $AllureExitCode = $LASTEXITCODE

    if ($AllureExitCode -ne 0) {
        throw "Allure报告生成失败，退出码：$AllureExitCode"
    }

    Write-Host "Allure报告已生成：" `
        -ForegroundColor Green

    Write-Host $ReportDir

    # 只有传入 -OpenReport 参数时才打开浏览器
    if ($OpenReport) {
        allure open $ReportDir
    }

    # 报告生成后，再根据Pytest退出码判断测试是否通过
    if ($PytestExitCode -ne 0) {
        throw "存在失败用例，请查看Allure报告。"
    }

    Write-Host "全部测试执行成功。" `
        -ForegroundColor Green
}
finally {
    # 无论成功还是失败，都返回执行脚本前的目录
    Pop-Location
}