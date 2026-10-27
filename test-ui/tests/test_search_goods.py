from pages.goods_page import GoodsPage
from pages.home_page import HomePage
from pages.search_page import SearchPage


def test_search_and_open_product(page, settings):
    home = HomePage(page, settings)
    search = SearchPage(page, settings)
    goods = GoodsPage(page, settings)

    home.open()
    home.go_to_search()
    search.search(settings.search_keyword)
    search.assert_product_found(settings.goods_name)
    search.open_product(settings.goods_name)
    goods.assert_product_opened(settings.goods_name)
