from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage


def test_submit_order_smoke(
    authenticated_page, cart_with_one_item, test_address, api_client, settings
):
    cart = CartPage(authenticated_page, settings)
    checkout = CheckoutPage(authenticated_page, settings)
    order_id = None

    try:
        cart.open()
        cart.assert_product_visible(settings.goods_name)
        cart.go_to_checkout()
        checkout.select_address(test_address["name"])
        checkout.assert_ready(settings.goods_name)
        order_id = checkout.submit_order()
        assert order_id > 0
        checkout.assert_payment_page()
        detail = api_client.order_detail(order_id)
        assert any(x["productId"] == settings.product_id and x["number"] == 1 for x in detail["orderGoods"])
    finally:
        if order_id is not None:
            api_client.cancel_and_delete_order(order_id)
