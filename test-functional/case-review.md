# 功能用例评审与结果关联

评审日期：2026-10-27。评审对象：`Litemall功能测试用例.xlsx`。

## 用例库评审

共 249 条：用户端 135 条、管理端 89 条、跨端闭环 25 条。八个字段均已填写，用例编号唯一，优先级均为 P0/P1/P2；保留黄色表头和普通正文样式。

本次修改 44 条用例中的 48 个单元格：

- 将用户端登录数据与本地专用测试账号对齐，管理端使用独立管理员数据。
- 补全优惠券、评价和售后用例中被截断的前置条件。
- 明确库存竞争、团购、角色权限和数据隔离场景中的独立 A/B 身份。
- 将搜索联想、搜索排序的页面范围修正为小程序。
- 细化登录、商品不存在、加购、地址、下单、重复提交及跨用户验证的步骤和数据清理。

评审结论：用例库的字段、编号、优先级及上述问题修正检查通过。

## 执行结果索引

以下结果来自已有专项执行记录，按各自的环境、日期和范围统计。

| 验证层次 | 执行日期 | 结果 | 证据 |
| --- | --- | --- | --- |
| 接口回归 | 2026-10-18 | 44 项：41 passed，3 xfailed | [接口说明](../test-automation/README.md)、[异常与权限报告](../test-automation/docs/api-abnormal-permission-test-report.md) |
| 基础安全（包含在上述 44 项内） | 2026-10-18 | 20 项：18 passed，2 xfailed | [安全报告](../test-automation/docs/basic-security-test-report.md) |
| H5 UI 自动化 | 2026-10-26 至 27 | 5 项通过；入口脚本复跑 11.39 秒 | [UI 执行记录](../test-ui/docs/ui-test-execution.md) |
| H5 浏览器与视口巡检 | 2026-10-16 | 28 项通过 | [兼容性报告](../test-compatibility/README.md) |
| 小程序开发者工具运行检查 | 2026-10-16 | 12 项通过 | [运行记录](../test-compatibility/results/miniprogram-runtime-2026-10-16/report.md) |

`xfail` 用于追踪可复现的已知产品缺陷，修复后应回归验证。安全子集与接口回归不重复累加。

## 重点缺陷关联

| 用例/场景 | 实际发现 | 缺陷记录 |
| --- | --- | --- |
| 加购输入校验 | 缺少 number 引发空指针，返回内部错误 | 禅道 #3；[请求与日志证据](../test-automation/docs/images/bugs/cart-missing-number/) |
| U-ORDER-008：重复提交 | 同一 cartId 重放后产生两个不同订单 | [响应与落库证据](../test-automation/docs/images/bugs/order-duplicate-submit/) |
| E2E-023：跨用户数据隔离 | B 使用 A 的购物车创建自己的订单，并逻辑删除 A 的购物车 | 禅道 #5；[权限与数据库证据](../test-automation/docs/images/bugs/order-cross-user-submit/) |

与自动化的对应关系为场景关联：一条功能用例可能包含多个验证点，不与自动化条目数量机械一一对应。
