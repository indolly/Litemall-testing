from playwright.sync_api import expect

from pages.base_page import BasePage


class CartPage(BasePage):
    def open(self) -> None:
        super().open("/order")

    def product_card(self, product_name: str):
        return self.page.locator(".van-card").filter(has_text=product_name)

    def assert_product_visible(self, product_name: str) -> None:
        expect(self.product_card(product_name)).to_be_visible()

    def change_quantity_to_two(self, product_name: str) -> None:
        self.page.get_by_text("编辑", exact=True).click()
        card = self.product_card(product_name)
        quantity = card.locator(".van-stepper__input")
        expect(quantity).to_have_value("1")
        with self.page.expect_response(
            lambda response: "/wx/cart/update" in response.url and response.status == 200
        ) as response_info:
            card.locator(".van-stepper__plus").click()
        payload = response_info.value.json()
        assert payload["errno"] == 0, payload
        expect(quantity).to_have_value("2")

    def assert_total(self, total: str) -> None:
        expect(self.page.locator(".van-submit-bar__price:not(.van-submit-bar__price--integer)")).to_contain_text(total)

    def go_to_checkout(self) -> None:
        checkout = self.page.get_by_role("button", name="结算", exact=True)
        expect(checkout).to_be_enabled()
        checkout.click()
        self.page.wait_for_url("**/#/order/checkout")
