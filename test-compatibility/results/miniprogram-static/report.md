# Litemall 微信小程序静态兼容性预检报告

- 开发者工具版本：2.02.2608070
- 项目基础库版本：2.4.0
- 页面数量：41
- JSON 文件数量：108
- 检查项：154，PASS 154，FAIL 0

## 风险与运行态关注点

| 等级 | 项目 | 说明 |
| --- | --- | --- |
| INFO | 真机访问限制 | http://127.0.0.1:8081/wx/ 只适用于开发者工具；真机中的 127.0.0.1 指向手机本身，真机测试需改为电脑局域网 IP 或测试环境 HTTPS 域名。 |
| RISK | 基础库版本 | project.config.json 固定为 2.4.0，版本较旧。运行态应至少覆盖项目版本 2.4.0 与开发者工具当前稳定基础库。 |
| INFO | 调试模式 | app.json 的 debug=true 适用于测试环境；发布构建前应关闭，避免保留额外调试信息。 |
| RISK | 兼容性敏感 API: wx.getSystemInfo | 使用位置：lib/wxParse/wxParse.js, pages/category/category.js。应在新基础库和目标机型上回归，并关注开发者工具的废弃提示。 |
| RISK | 兼容性敏感 API: wx.chooseImage | 使用位置：lib/vant-weapp/uploader/index.js, pages/commentPost/commentPost.js, pages/topicCommentPost/topicCommentPost.js, pages/ucenter/feedback/feedback.js。应在新基础库和目标机型上回归，并关注开发者工具的废弃提示。 |

## 静态检查明细

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 页面四件套: pages/index/index | PASS | 文件齐全 |
| 页面四件套: pages/catalog/catalog | PASS | 文件齐全 |
| 页面四件套: pages/newGoods/newGoods | PASS | 文件齐全 |
| 页面四件套: pages/hotGoods/hotGoods | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/index/index | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/address/address | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/addressAdd/addressAdd | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/feedback/feedback | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/footprint/footprint | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/order/order | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/orderDetail/orderDetail | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/couponList/couponList | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/couponSelect/couponSelect | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/collect/collect | PASS | 文件齐全 |
| 页面四件套: pages/auth/login/login | PASS | 文件齐全 |
| 页面四件套: pages/auth/accountLogin/accountLogin | PASS | 文件齐全 |
| 页面四件套: pages/auth/register/register | PASS | 文件齐全 |
| 页面四件套: pages/auth/reset/reset | PASS | 文件齐全 |
| 页面四件套: pages/payResult/payResult | PASS | 文件齐全 |
| 页面四件套: pages/comment/comment | PASS | 文件齐全 |
| 页面四件套: pages/commentPost/commentPost | PASS | 文件齐全 |
| 页面四件套: pages/topic/topic | PASS | 文件齐全 |
| 页面四件套: pages/topicComment/topicComment | PASS | 文件齐全 |
| 页面四件套: pages/topicDetail/topicDetail | PASS | 文件齐全 |
| 页面四件套: pages/topicCommentPost/topicCommentPost | PASS | 文件齐全 |
| 页面四件套: pages/brand/brand | PASS | 文件齐全 |
| 页面四件套: pages/brandDetail/brandDetail | PASS | 文件齐全 |
| 页面四件套: pages/search/search | PASS | 文件齐全 |
| 页面四件套: pages/category/category | PASS | 文件齐全 |
| 页面四件套: pages/cart/cart | PASS | 文件齐全 |
| 页面四件套: pages/checkout/checkout | PASS | 文件齐全 |
| 页面四件套: pages/goods/goods | PASS | 文件齐全 |
| 页面四件套: pages/about/about | PASS | 文件齐全 |
| 页面四件套: pages/groupon/myGroupon/myGroupon | PASS | 文件齐全 |
| 页面四件套: pages/groupon/grouponDetail/grouponDetail | PASS | 文件齐全 |
| 页面四件套: pages/groupon/grouponList/grouponList | PASS | 文件齐全 |
| 页面四件套: pages/coupon/coupon | PASS | 文件齐全 |
| 页面四件套: pages/help/help | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/aftersale/aftersale | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/aftersaleList/aftersaleList | PASS | 文件齐全 |
| 页面四件套: pages/ucenter/aftersaleDetail/aftersaleDetail | PASS | 文件齐全 |
| TabBar: 首页 | PASS | 路由和图标有效 |
| TabBar: 分类 | PASS | 路由和图标有效 |
| TabBar: 购物车 | PASS | 路由和图标有效 |
| TabBar: 个人 | PASS | 路由和图标有效 |
| JSON: app.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/action-sheet/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/area/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/button/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/card/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/cell/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/cell-group/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/checkbox/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/checkbox-group/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/circle/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/col/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/collapse/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/collapse-item/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/count-down/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/datetime-picker/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/dialog/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/divider/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/dropdown-item/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/dropdown-menu/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/field/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/goods-action/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/goods-action-button/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/goods-action-icon/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/grid/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/grid-item/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/icon/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/image/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/index-anchor/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/index-bar/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/info/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/loading/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/nav-bar/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/notice-bar/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/notify/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/overlay/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/panel/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/picker/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/picker-column/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/popup/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/progress/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/radio/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/radio-group/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/rate/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/row/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/search/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/sidebar/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/sidebar-item/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/skeleton/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/slider/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/stepper/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/steps/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/sticky/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/submit-bar/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/swipe-cell/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/switch/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/tab/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/tabbar/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/tabbar-item/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/tabs/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/tag/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/toast/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/transition/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/tree-select/index.json | PASS | 语法有效 |
| JSON: lib/vant-weapp/uploader/index.json | PASS | 语法有效 |
| JSON: pages/about/about.json | PASS | 语法有效 |
| JSON: pages/auth/accountLogin/accountLogin.json | PASS | 语法有效 |
| JSON: pages/auth/login/login.json | PASS | 语法有效 |
| JSON: pages/auth/register/register.json | PASS | 语法有效 |
| JSON: pages/auth/reset/reset.json | PASS | 语法有效 |
| JSON: pages/brand/brand.json | PASS | 语法有效 |
| JSON: pages/brandDetail/brandDetail.json | PASS | 语法有效 |
| JSON: pages/cart/cart.json | PASS | 语法有效 |
| JSON: pages/catalog/catalog.json | PASS | 语法有效 |
| JSON: pages/category/category.json | PASS | 语法有效 |
| JSON: pages/checkout/checkout.json | PASS | 语法有效 |
| JSON: pages/comment/comment.json | PASS | 语法有效 |
| JSON: pages/commentPost/commentPost.json | PASS | 语法有效 |
| JSON: pages/coupon/coupon.json | PASS | 语法有效 |
| JSON: pages/goods/goods.json | PASS | 语法有效 |
| JSON: pages/groupon/grouponDetail/grouponDetail.json | PASS | 语法有效 |
| JSON: pages/groupon/grouponList/grouponList.json | PASS | 语法有效 |
| JSON: pages/groupon/myGroupon/myGroupon.json | PASS | 语法有效 |
| JSON: pages/help/help.json | PASS | 语法有效 |
| JSON: pages/hotGoods/hotGoods.json | PASS | 语法有效 |
| JSON: pages/index/index.json | PASS | 语法有效 |
| JSON: pages/newGoods/newGoods.json | PASS | 语法有效 |
| JSON: pages/payResult/payResult.json | PASS | 语法有效 |
| JSON: pages/search/search.json | PASS | 语法有效 |
| JSON: pages/topic/topic.json | PASS | 语法有效 |
| JSON: pages/topicComment/topicComment.json | PASS | 语法有效 |
| JSON: pages/topicCommentPost/topicCommentPost.json | PASS | 语法有效 |
| JSON: pages/topicDetail/topicDetail.json | PASS | 语法有效 |
| JSON: pages/ucenter/address/address.json | PASS | 语法有效 |
| JSON: pages/ucenter/addressAdd/addressAdd.json | PASS | 语法有效 |
| JSON: pages/ucenter/aftersale/aftersale.json | PASS | 语法有效 |
| JSON: pages/ucenter/aftersaleDetail/aftersaleDetail.json | PASS | 语法有效 |
| JSON: pages/ucenter/aftersaleList/aftersaleList.json | PASS | 语法有效 |
| JSON: pages/ucenter/collect/collect.json | PASS | 语法有效 |
| JSON: pages/ucenter/couponList/couponList.json | PASS | 语法有效 |
| JSON: pages/ucenter/couponSelect/couponSelect.json | PASS | 语法有效 |
| JSON: pages/ucenter/feedback/feedback.json | PASS | 语法有效 |
| JSON: pages/ucenter/footprint/footprint.json | PASS | 语法有效 |
| JSON: pages/ucenter/index/index.json | PASS | 语法有效 |
| JSON: pages/ucenter/order/order.json | PASS | 语法有效 |
| JSON: pages/ucenter/orderDetail/orderDetail.json | PASS | 语法有效 |
| JSON: project.config.json | PASS | 语法有效 |
| JSON: project.private.config.json | PASS | 语法有效 |
| JSON: sitemap.json | PASS | 语法有效 |
| 本地接口配置 | PASS | http://127.0.0.1:8081/wx/ |

## 边界说明

静态预检只能证明工程文件、路由和配置结构完整，不能替代开发者工具模拟器与真机运行测试。
完成运行态兼容性测试前，不应把本报告描述为“小程序兼容性全部通过”。
