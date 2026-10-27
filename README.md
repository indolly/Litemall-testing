# Litemall 电商系统测试实践

本项目围绕 Litemall 电商系统开展功能用例设计、接口自动化、H5 UI 自动化、权限与数据隔离、兼容性及性能测试实践，结合 Docker、MySQL、服务日志和资源监控验证系统行为。

项目重点不是单纯堆积测试用例，而是通过“接口响应、业务状态、数据库记录、服务端资源”四个层面验证系统行为，并保留可复现的脚本、报告说明和结果截图。

## 项目成果概览

| 测试方向 | 已完成内容 |
| --- | --- |
| 环境部署与排错 | 使用 Docker Compose 部署 Litemall 与 MySQL，排查端口冲突、容器时区、数据库连接和服务日志问题 |
| 功能测试 | 设计并评审 249 条功能用例：用户端 135 条、管理端 89 条、跨端闭环 25 条；按正常、异常、边界、状态、权限及数据一致性组织 |
| 接口自动化 | 使用 Python、Requests、Pytest 构建 44 条核心接口回归用例，覆盖认证、商品、地址、购物车、订单、异常输入与对象级权限 |
| 数据库校验 | 使用 PyMySQL 验证订单主表、订单商品表、SKU 库存、状态变化和逻辑删除 |
| 测试报告 | 使用 Allure 展示业务步骤、动态参数、环境信息及失败诊断附件 |
| H5 UI 自动化 | 使用 Playwright + Pytest + 页面对象封装覆盖登录、搜索、加购编辑数量、结算下单，5 条场景通过；自动准备与清理数据 |
| 基础安全 | 20 条安全子集覆盖认证、Token、对象级授权、参数篡改与敏感字段，18 passed、2 xfailed；已包含在 44 条接口用例中 |
| 兼容性测试 | 使用 Chrome DevTools Protocol 验证 Chrome、Edge 的桌面与移动视口，并在微信开发者工具中执行小程序核心场景 |
| 性能测试 | 使用 JMeter 完成基准、负载、压力和稳定性测试，并结合 Docker 资源监控进行分析 |
| 性能实验 | 对 Druid 连接池和 Tomcat 工作线程开展控制变量 A/B 实验，验证调优假设 |
| 工程化 | 编写 PowerShell 脚本，实现测试执行、Docker 监控、结果汇总和 HTML 报告生成 |
| 持续集成 | 配置 GitHub Actions：构建被测后端、启动 Docker 服务、运行 Pytest、归档 JUnit / Allure 原始结果及日志 |

功能用例、评审修正及执行证据索引见[功能测试说明](test-functional/README.md)与[用例评审记录](test-functional/case-review.md)。

## 自动化测试结果

当前核心回归集包含 44 条用例，本地结果为 `41 passed, 3 xfailed`。3 条 `xfail` 对应已经复现并登记、尚未修复的产品缺陷，而不是测试通过。覆盖范围包括：

- 正确登录、错误密码、空用户名和不存在用户；
- 商品存在与不存在搜索；
- 购物车正常鉴权、无 Token、非法 Token、参数边界和重复操作；
- 订单结算、提交、详情查询、数据库落库、库存扣减与恢复、取消及逻辑删除；
- 地址数据准备、重复提交和跨用户对象访问等权限场景；
- 过期 Token、敏感字段、参数篡改以及地址/订单对象级授权。

详细设计、运行方法和订单链路说明见 [接口自动化测试说明](test-automation/README.md)。

基础安全场景、权限断言、缺陷证据及修复建议见[安全测试报告](test-automation/docs/basic-security-test-report.md)。

## H5 UI 自动化结果

使用 Python、Pytest、Playwright，将页面操作封装为 Page Object，通过 fixture 管理独立浏览器会话及测试数据。覆盖正确登录、错误密码、搜索打开商品、页面加购与数量修改、购物车结算提交订单五个场景。

本机 Chrome、390×844 视口，最终入口脚本运行结果为 `5 passed，11.39 秒`。交易用例同时核对页面与接口结果，结束后取消并逻辑删除测试订单、清理临时地址、恢复购物车内容并检查库存恢复。

运行方法见[UI 自动化说明](test-ui/README.md)，日期、环境及结果见[执行记录](test-ui/docs/ui-test-execution.md)。

## H5 与微信小程序兼容性测试结果

H5 使用本机 Chrome 155 和 Edge 155，分别在桌面 `1440×900` 与移动 `390×844` 视口执行首页、分类、搜索、商品详情、登录、订单入口和个人中心巡检，共 `28 PASS、0 FAIL`。检查内容包含正文渲染、横向溢出、破图、JavaScript 异常、HTTP 4xx/5xx 和关键资源失败。

微信小程序先完成 41 个页面、108 个 JSON 文件及页面四件套的静态预检，共 `154 PASS、0 FAIL`；随后在微信开发者工具的 iPhone 12/13 Pro 模拟器、微信 8.0.5、基础库 3.17.3 环境中执行首页、搜索、商品详情、登录、购物车、订单、地址和结算等 12 个运行场景，结果为 `12 PASS、0 产品失败`。

兼容性矩阵、执行边界、原始结果和截图证据见 [兼容性测试说明](test-compatibility/README.md)。当前结论只覆盖指定浏览器、视口和开发者工具模拟器，不替代 Safari/WebKit、Android 与 iOS 真机验证。

## 性能测试结果

商城首页接口在当前本地测试环境中的逐级压力测试结果如下：

| 并发用户数 | 吞吐量（次/秒） | 平均响应时间（ms） | P95（ms） | P99（ms） | 错误率 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 35.70 | 11.18 | 16 | 19 | 0.00% |
| 50 | 88.60 | 11.99 | 18 | 23 | 0.00% |
| 100 | 176.40 | 14.59 | 27 | 50 | 0.00% |
| 200 | 347.00 | 23.17 | 46 | 109 | 0.00% |
| 300 | 388.26 | 202.95 | 355 | 419 | 0.00% |

从 200 增加到 300 并发用户时，吞吐量仅增加约 11.9%，平均响应时间约上升至原来的 8.8 倍。因此，在当前机器、接口和负载模型下，可以判断性能拐点位于 200 至 300 并发用户之间。

![300 用户压力测试](test-performance/docs/screenshots/home-stress-300u-statistics.png)

100 用户持续运行 10 分钟，共完成 113,015 次请求，错误率为 0.00%，吞吐量为 188.54 次/秒；测试时间窗口内未观察到明显的持续响应恶化或内存泄漏迹象。

![稳定性测试结果](test-performance/docs/screenshots/home-stability-100u-10m-statistics.png)

详细的测试模型、参数说明、A/B 实验、资源分析和限制说明见 [性能测试说明](test-performance/README.md)。

## 性能调用链理解

```text
JMeter
  → Tomcat 工作线程
  → WxHomeController
  → 首页内部任务线程池
  → Service
  → Mapper / MyBatis
  → Druid 数据库连接池
  → MySQL
  → 返回 HTTP 响应
```

本项目验证了单独把 Druid 最大活跃连接数从 50 增加到 100，以及把 Tomcat 最大工作线程数从 200 增加到 400，均未改善 300 并发场景的性能。该结果说明这两项配置不是简单“调大就更快”，但现有证据不足以断言唯一性能根因。

## 项目结构

```text
litemall
├─ test-functional           # 249 条 Excel 用例、覆盖矩阵与评审记录
├─ test-automation
│  ├─ tests                  # Pytest 接口自动化用例与 fixture
│  ├─ docs/images            # Pytest 和 Allure 结果截图
│  ├─ requirements.txt       # Python 依赖
│  ├─ run_tests.ps1          # 自动执行并生成 Allure 报告
│  └─ README.md              # 接口自动化详细说明
├─ test-performance
│  ├─ jmeter                 # JMeter 测试计划
│  ├─ scripts                # 执行、监控和分析脚本
│  ├─ docs/screenshots       # 性能测试证据截图
│  └─ README.md              # 性能测试详细报告
├─ test-compatibility
│  ├─ scripts                # H5 巡检与小程序静态预检脚本
│  ├─ results                # 兼容性报告、结构化结果和关键截图
│  └─ README.md              # 兼容性矩阵、结论与测试边界
├─ test-ui                   # Playwright 页面对象、场景、数据准备清理及执行记录
├─ .github/workflows         # 接口自动化持续集成配置
├─ docker                    # Docker Compose 与服务配置
└─ pytest.ini                # Pytest 项目配置
```

生成的 Allure 报告、JMeter JTL/HTML 报告、Docker 原始监控文件和数据库运行数据不提交到 GitHub，避免仓库包含大量可重复生成的临时文件。项目保留测试代码、执行脚本、说明文档和关键结果截图。

## 快速运行接口自动化

运行前需要启动 Docker Desktop、Litemall 后端和 MySQL。

首次使用时，先在项目根目录创建本机私有配置：

```powershell
Copy-Item .\test-automation\test_config.example.json `
  .\test-automation\test_config.local.json
```

然后打开 `test_config.local.json`，填写自己环境中的接口地址、测试账号和数据库连接信息。该文件已被 Git 忽略，不会上传到 GitHub。

在项目根目录执行：

```powershell
python -m pip install -r .\test-automation\requirements.txt
powershell.exe -ExecutionPolicy Bypass -File .\test-automation\run_tests.ps1
```

## 快速运行性能测试

JMeter 安装完成且服务可访问后，在项目根目录执行：

```powershell
powershell.exe -ExecutionPolicy Bypass `
  -File .\test-performance\scripts\run_performance_test.ps1 `
  -RunName "home-smoke-1u" `
  -Users 1 `
  -RampUp 1 `
  -Duration 10 `
  -Delay 500
```

参数含义、正式压测命令及输出文件关系请查看性能测试目录中的 README。

## Docker 私有配置

首次使用 Docker Compose 前执行：

```powershell
Copy-Item .\docker\.env.example .\docker\.env
```

在 `docker/.env` 中填写本机数据库密码等配置。`docker/.env.example` 只提供字段模板，真实 `docker/.env` 不会进入 Git 仓库。

## 测试边界

- 性能结果来自本地 Windows、Docker Desktop 环境，不能直接等同于生产容量；
- 当前性能测试主要覆盖商城首页接口，不代表全业务链路性能；
- 当前自动化用例是核心回归集，并非 Litemall 全量测试覆盖；
- 配置实验主要执行一次，正式容量评估还需要同配置多轮重复并比较中位数；
- 当前没有完整 JVM、慢 SQL、锁等待和分布式监控数据，因此不宣称已定位唯一性能瓶颈。
