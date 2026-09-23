from decimal import Decimal

import allure
import requests

from settings import BASE_URL

@allure.epic("Litemall 商城")
@allure.feature("购物车管理")
@allure.story("查询购物车")
@allure.title("登录用户成功查询购物车及汇总金额")
@allure.severity(allure.severity_level.CRITICAL)
def test_get_cart_success(api_session):
    response=api_session.get(
        f"{BASE_URL}/wx/cart/index",
        timeout=5,
    )

    body=response.json()

    assert response.status_code==200
    assert body["errno"]==0

    cart_list=body["data"]["cartList"]
    cart_total=body["data"]["cartTotal"]

    assert isinstance(cart_list,list)

    calculated_count=sum(item["number"] for item in cart_list)  #购物车所有物品总数
    calculated_amount=sum(
        (
            Decimal(str(item["price"])) * item["number"]
            for item in cart_list
        ),
        Decimal("0"),
    )

    assert calculated_count==cart_total["goodsCount"]
    assert calculated_amount==Decimal(str(cart_total["goodsAmount"]))

@allure.epic("Litemall 商城")
@allure.feature("购物车管理")
@allure.story("访问权限")
@allure.title("未携带Token查询购物车被拒绝")
@allure.severity(allure.severity_level.CRITICAL)
#缺少token
def test_get_cart_without_token():
    response=requests.get(
        f"{BASE_URL}/wx/cart/index",
        timeout=5,
    )
    body=response.json()

    assert response.status_code==200
    assert body["errno"]==501
    assert body["errmsg"]=="请登录"
    assert not body.get("data")


@allure.epic("Litemall 商城")
@allure.feature("购物车管理")
@allure.story("访问权限")
@allure.title("携带无效Token查询购物车被拒绝")
#伪造或无效token
def test_get_cart_invalid_token():
    response=requests.get(
        f"{BASE_URL}/wx/cart/index",
        headers={
            "X-Litemall-Token":"invalid_token_123456",
        },
        timeout=5,
    )
    body=response.json()

    assert response.status_code==200
    assert body["errno"]==501
    assert body["errmsg"]=="请登录"
    assert not body.get("data")
