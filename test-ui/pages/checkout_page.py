from playwright.sync_api import expect

from pages.base_page import BasePage


class CheckoutPage(BasePage):
    def select_address(self, address_name: str) -> None:
        self.page.get_by_text("收货地址", exact=True).click()
        self.page.locator(".van-address-item").filter(has_text=address_name).locator(".van-radio").click()
        self.page.wait_for_url("**/#/order/checkout")
        expect(self.page.get_by_text(address_name, exact=True)).to_be_visible()

    def assert_ready(self, product_name: str) -> None:
        expect(self.page.get_by_text("商品金额", exact=True)).to_be_visible()
        expect(self.page.get_by_text(product_name, exact=True)).to_be_visible()
        expect(self.page.get_by_text("收货地址", exact=True)).to_be_visible()

    def submit_order(self) -> int:
        with self.page.expect_response(
            lambda response: "/wx/order/submit" in response.url and response.status == 200
        ) as response_info:
            self.page.get_by_role("button", name="提交订单", exact=True).click()

        payload = response_info.value.json()
        assert payload["errno"] == 0, payload
        order_id = payload["data"]["orderId"]
        return order_id

    def assert_payment_page(self) -> None:
        expect(self.page).to_have_url(self.settings.page_url("/order/payment"))
        expect(self.page.get_by_text("订单编号", exact=True)).to_be_visible()
        expect(self.page.get_by_role("button", name="去支付", exact=True)).to_be_visible()
