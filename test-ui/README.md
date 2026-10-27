# Litemall H5 UI 自动化

本目录使用 Python、Pytest 和 Playwright 覆盖少量高价值 H5 主链，不把全部功能用例机械搬到 UI 层。

## 当前用例

1. 正确账号登录成功。
2. 错误密码登录失败。
3. 搜索并打开目标商品。
4. 在商品详情页选择规格并加入购物车，将数量从 1 修改为 2，核对页面合计与接口持久化结果。
5. 购物车结算，选择临时地址并提交订单，核对付款页面及订单商品，完成后自动取消、逻辑删除测试订单。

本地验证结果：Windows / 本机 Chrome / 390×844 视口，5 passed；最终入口脚本复跑 11.39 秒。日期与轮次见[执行记录](docs/ui-test-execution.md)。

## 目录职责

- `pages/`：页面定位器与页面操作，避免测试里重复写选择器。
- `tests/`：业务场景、执行步骤和关键断言。
- `support/api_client.py`：通过接口准备和清理购物车、订单测试数据。
- `config/settings.py`：URL、测试账号、商品等可覆盖配置。
- `artifacts/`：JUnit 执行结果、失败时生成的截图和 trace，由 Git 忽略。取证文件可能包含登录态或测试数据，保存在本机。
- `run_ui_tests.ps1`：运行前检查服务，再统一执行用例。

## 在 VS Code 中运行

1. 通过“文件 → 打开文件夹”打开包含 `test-ui` 的测试目录。本机源码工作目录为 `D:\study\softtest\Litemall\litemall`，待发布测试仓库为 `D:\study\softtest\Litemall\Litemall-testing-publish`。
2. 打开“终端 → 新建终端”，确认后端 `8081` 已启动。
3. 点击终端右上角 `+` 新建第二个终端：

   ```powershell
   cd D:\study\softtest\Litemall\litemall\litemall-vue
   npm run dev
   ```

4. H5 编译成功后，回到测试目录的第一个终端执行：

   ```powershell
   .\test-ui\run_ui_tests.ps1
   ```

只运行登录模块并显示浏览器，适合首次阅读代码：

```powershell
.\test-ui\run_ui_tests.ps1 -LoginOnly -Headed
```

显示浏览器运行全部场景：

```powershell
.\test-ui\run_ui_tests.ps1 -Headed
```

## 配置覆盖

默认使用 `user123/user123`。企业环境不应把真实密码写进仓库，可在 PowerShell 临时设置：

```powershell
$env:UI_USERNAME = "测试账号"
$env:UI_PASSWORD = "测试密码"
.\test-ui\run_ui_tests.ps1
```

`UI_WEB_BASE_URL`、`UI_API_BASE_URL` 可覆盖页面和接口地址。`UI_BROWSER_CHANNEL=msedge` 可切换本机 Edge；本次验证使用 Chrome。

## 测试数据和执行范围

使用专用本地测试账号串行执行。购物车 fixture 会保存原商品、数量和勾选状态，运行后恢复；被下单消耗的购物车记录如需重新创建，记录 ID 可能变化。运行时不要同时手动操作这个账号。

订单用例通过 API 新建带唯一姓名的临时地址，再在页面中选择该地址。通过 API 准备购物车后，从购物车页面点击结算、选择地址、提交订单并验证待付款页面。用例不会点击“去支付”。

清理使用业务 API：取消本次订单恢复库存，逻辑删除本次订单和地址，恢复购物车内容。逻辑删除后的审计记录仍会留在数据库；每条交易测试结束会核对 SKU 库存是否回到原值。

框架使用独立 BrowserContext 隔离每条测试的 Cookie 和 LocalStorage。登录用例真实输入账号密码；其他场景通过 API 登录后把 Token 写入该测试的页面会话。

## 安装和失败排查

被测 H5 源码位于系统项目的 `litemall-vue`，测试资产仓库单独保存自动化代码。其他机器按实际源码位置启动 H5。

依赖记录在 `requirements.txt`。首次运行先在测试目录的终端创建虚拟环境（已有时跳过第一行）：

```powershell
python -m venv .\test-automation\.venv
& ".\test-automation\.venv\Scripts\python.exe" -m pip install -r .\test-ui\requirements.txt
```

默认驱动本机已安装的 Chrome，无须额外下载 Chromium。若没有 Chrome，可设置 `UI_BROWSER_CHANNEL=msedge` 使用本机 Edge。

用例失败时先在 VS Code 左侧打开 `test-ui/artifacts`，查看对应测试目录中的 PNG 截图与 `trace.zip`。在项目根目录终端执行以下命令，再通过 Trace Viewer 的文件选择框打开对应 `trace.zip`：

```powershell
& ".\test-automation\.venv\Scripts\python.exe" -m playwright show-trace
```

Trace 包含操作时间线、页面快照和网络信息。先看失败步骤，再确认元素是否唯一、请求是否发出、业务响应是否成功。不要通过固定 sleep 或无条件重跑掩盖问题。
