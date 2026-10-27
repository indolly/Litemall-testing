from playwright.sync_api import expect

from pages.base_page import BasePage


class GoodsPage(BasePage):
    def open(self, goods_id: int) -> None:
        super().open(f"/items/detail/{goods_id}")

    @property
    def title(self):
        return self.page.locator(".item-title")

    def assert_product_opened(self, product_name: str) -> None:
        expect(self.title).to_have_text(product_name)

    def add_standard_product_to_cart(self) -> None:
        self.page.locator(".van-goods-action").get_by_role("button", name="加入购物车", exact=True).click()
        popup = self.page.locator(".van-sku-container")
        expect(popup).to_be_visible()
        popup.get_by_text("标准", exact=True).click()
        with self.page.expect_response(lambda response: "/wx/cart/add" in response.url) as response_info:
            popup.get_by_role("button", name="加入购物车", exact=True).click()
        payload = response_info.value.json()
        assert payload["errno"] == 0, payload
        expect(popup).not_to_be_visible()
