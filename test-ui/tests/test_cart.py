from pages.cart_page import CartPage
from pages.goods_page import GoodsPage


def test_edit_cart_quantity(authenticated_page, isolated_cart, api_client, settings):
    goods = GoodsPage(authenticated_page, settings)
    goods.open(settings.goods_id)
    goods.assert_product_opened(settings.goods_name)
    goods.add_standard_product_to_cart()
    cart = CartPage(authenticated_page, settings)
    cart.open()
    cart.assert_product_visible(settings.goods_name)
    cart.change_quantity_to_two(settings.goods_name)
    item = next(x for x in api_client.cart_items() if x["productId"] == settings.product_id)
    assert item["number"] == 2
    cart.assert_total(f'{float(item["price"]) * 2:.2f}')
