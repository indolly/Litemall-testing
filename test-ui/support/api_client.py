from playwright.sync_api import APIRequestContext, Playwright

from config.settings import Settings


class ApiClient:
    """只负责 UI 用例的测试数据准备与清理，不代替 UI 业务断言。"""

    def __init__(self, playwright: Playwright, settings: Settings):
        self.settings = settings
        api_base = settings.api_base_url.rstrip("/") + "/"
        anonymous = playwright.request.new_context(base_url=api_base, timeout=15000)
        try:
            response = anonymous.post(
                "auth/login",
                data={"username": settings.username, "password": settings.password},
            )
            self._assert_ok(response, "登录")
            payload = response.json()["data"]
            self.token = payload["token"]
            self.nickname = payload["userInfo"]["nickName"]
        finally:
            anonymous.dispose()

        self.request: APIRequestContext = playwright.request.new_context(
            base_url=api_base,
            timeout=15000,
            extra_http_headers={"X-Litemall-Token": self.token},
        )

    @staticmethod
    def _assert_ok(response, action: str) -> dict:
        assert response.ok, f"{action} HTTP 失败：{response.status}"
        payload = response.json()
        assert payload["errno"] == 0, f"{action}业务失败：{payload}"
        return payload

    def close(self) -> None:
        self.request.dispose()

    def remove_test_product(self) -> None:
        response = self.request.post(
            "cart/delete", data={"productIds": [self.settings.product_id]}
        )
        self._assert_ok(response, "清理购物车")

    def add_test_product(self, number: int = 1) -> None:
        self.remove_test_product()
        response = self.request.post(
            "cart/add",
            data={
                "goodsId": self.settings.goods_id,
                "productId": self.settings.product_id,
                "number": number,
            },
        )
        self._assert_ok(response, "准备购物车")

    def cancel_and_delete_order(self, order_id: int) -> None:
        info = self.order_detail(order_id)["orderInfo"]
        if info["handleOption"]["cancel"]:
            cancel = self.request.post("order/cancel", data={"orderId": order_id})
            self._assert_ok(cancel, "取消测试订单")

        info = self.order_detail(order_id)["orderInfo"]
        assert info["handleOption"]["delete"], f"测试订单尚不可删除：{info}"

        delete = self.request.post("order/delete", data={"orderId": order_id})
        self._assert_ok(delete, "删除测试订单")

    def cart_items(self) -> list:
        response = self.request.get("cart/index")
        return self._assert_ok(response, "查询购物车")["data"]["cartList"]

    def check_products(self, product_ids: list, checked: bool) -> None:
        if product_ids:
            response = self.request.post(
                "cart/checked", data={"productIds": product_ids, "isChecked": int(checked)}
            )
            self._assert_ok(response, "修改购物车勾选")

    def restore_cart(self, original: list) -> None:
        """恢复原商品的数量与勾选；只移除本用例新增的目标商品。"""
        target = next((x for x in original if x["productId"] == self.settings.product_id), None)
        current = self.cart_items()
        if target is None:
            self.remove_test_product()
        else:
            existing = next((x for x in current if x["productId"] == target["productId"]), None)
            if existing is None:
                response = self.request.post("cart/add", data={
                    "goodsId": target["goodsId"], "productId": target["productId"],
                    "number": target["number"],
                })
            else:
                response = self.request.post("cart/update", data={
                    "id": existing["id"], "goodsId": target["goodsId"],
                    "productId": target["productId"], "number": target["number"],
                })
            self._assert_ok(response, "恢复原购物车数量")
        for checked in (False, True):
            self.check_products(
                [x["productId"] for x in original if bool(x["checked"]) == checked], checked
            )

    def create_address(self, label: str) -> int:
        response = self.request.post("address/save", data={
            "name": label, "tel": "13800138000", "province": "北京市",
            "city": "北京市", "county": "东城区", "areaCode": "110101",
            "addressDetail": "UI自动化测试路1号", "isDefault": False,
        })
        return self._assert_ok(response, "准备临时地址")["data"]

    def delete_address(self, address_id: int) -> None:
        self._assert_ok(self.request.post("address/delete", data={"id": address_id}), "清理临时地址")

    def order_detail(self, order_id: int) -> dict:
        response = self.request.get("order/detail", params={"orderId": order_id})
        return self._assert_ok(response, "查询订单详情")["data"]

    def product_stock(self) -> int:
        response = self.request.get("goods/detail", params={"id": self.settings.goods_id})
        data = self._assert_ok(response, "查询商品库存")["data"]
        product = next(x for x in data["productList"] if x["id"] == self.settings.product_id)
        return product["number"]
