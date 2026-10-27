from playwright.sync_api import expect

from pages.base_page import BasePage


class SearchPage(BasePage):
    @property
    def search_input(self):
        return self.page.locator("input[placeholder='请输入商品名称']")

    def search(self, keyword: str) -> None:
        self.search_input.fill(keyword)
        with self.page.expect_response(
            lambda response: "/wx/goods/list" in response.url and response.status == 200
        ):
            self.search_input.press("Enter")

    def product_card(self, product_name: str):
        return self.page.locator(".van-card").filter(has_text=product_name)

    def assert_product_found(self, product_name: str) -> None:
        expect(self.product_card(product_name)).to_have_count(1)
        expect(self.product_card(product_name)).to_be_visible()

    def open_product(self, product_name: str) -> None:
        self.product_card(product_name).click()
