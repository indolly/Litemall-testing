param([switch]$Headed, [switch]$LoginOnly)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "test-automation\.venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "未找到项目虚拟环境：$python"
}

if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port 8081 -InformationLevel Quiet)) {
    throw "Litemall 后端未启动：127.0.0.1:8081"
}

if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port 6255 -InformationLevel Quiet)) {
    throw "H5 前端未启动：127.0.0.1:6255。请先在 litemall-vue 目录执行 npm run dev"
}

Push-Location $PSScriptRoot
try {
    $arguments = @("-m", "pytest", "--junitxml=artifacts/results.xml")
    if ($Headed) { $arguments += "--headed" }
    if ($LoginOnly) { $arguments += "tests/test_login.py" }
    & $python @arguments
    $testExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $testExitCode
