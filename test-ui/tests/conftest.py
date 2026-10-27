import json
import uuid

import pytest

from config.settings import SETTINGS, Settings
from support.api_client import ApiClient


@pytest.fixture(scope="session")
def settings() -> Settings:
    return SETTINGS


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, settings):
    """复用电脑已安装的 Chrome，避免额外下载 Chromium 占用磁盘。"""
    return {**browser_type_launch_args, "channel": settings.browser_channel}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 390, "height": 844},
        "locale": "zh-CN",
    }


@pytest.fixture(scope="session")
def api_client(playwright, settings):
    client = ApiClient(playwright, settings)
    yield client
    client.close()


@pytest.fixture
def authenticated_page(page, api_client, settings):
    auth_script = (
        f"localStorage.setItem('Authorization', {json.dumps(api_client.token)});"
        f"localStorage.setItem('nickName', {json.dumps(api_client.nickname)});"
    )
    # 仅在当前 context 初始化一次，避免每次跳转都重新写入登录态。
    page.goto(settings.page_url("/"), wait_until="domcontentloaded")
    page.evaluate(auth_script)
    page.reload(wait_until="domcontentloaded")
    return page


@pytest.fixture
def isolated_cart(api_client, settings):
    original = api_client.cart_items()
    stock = api_client.product_stock()
    try:
        api_client.remove_test_product()
        api_client.check_products([x["productId"] for x in original if x["productId"] != settings.product_id], False)
        yield
    finally:
        api_client.restore_cart(original)
        assert api_client.product_stock() == stock, "测试结束后 SKU 库存未恢复"


@pytest.fixture
def cart_with_one_item(api_client, isolated_cart):
    api_client.add_test_product(number=1)


@pytest.fixture
def test_address(api_client):
    label = "UI测试" + uuid.uuid4().hex[:8]
    address_id = api_client.create_address(label)
    try:
        yield {"id": address_id, "name": label}
    finally:
        api_client.delete_address(address_id)
