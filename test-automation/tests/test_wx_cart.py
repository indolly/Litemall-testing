from decimal import Decimal

import allure
import pytest
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


@pytest.mark.parametrize(
    "number",
    [0, -1],
    ids=["zero", "negative"],
)
@allure.epic("Litemall 商城")
@allure.feature("购物车管理")
@allure.story("数量边界")
@allure.title("购物车拒绝非正数数量：{param_id}")
@allure.severity(allure.severity_level.CRITICAL)
def test_add_cart_rejects_non_positive_number(
        api_session,
        available_product,
        number,
        ):
    response = api_session.post(
        f"{BASE_URL}/wx/cart/add",
        json={
            "goodsId": available_product["goods_id"],
            "productId": available_product["product_id"],
            "number": number,
        },
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 401
    assert body["errmsg"] == "参数不对"


@allure.epic("Litemall 商城")
@allure.feature("购物车管理")
@allure.story("库存边界")
@allure.title("加入购物车数量超过库存时被拒绝")
@allure.severity(allure.severity_level.CRITICAL)
def test_add_cart_rejects_number_over_stock(
        api_session,
        available_product,
        ):
    response = api_session.post(
        f"{BASE_URL}/wx/cart/add",
        json={
            "goodsId": available_product["goods_id"],
            "productId": available_product["product_id"],
            "number": available_product["stock"] + 1,
        },
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 711
    assert body["errmsg"] == "库存不足"


@pytest.mark.xfail(
    strict=True,
    reason="已知缺陷：缺少number时后端空指针并返回errno=502，预期应返回401",
)
@allure.epic("Litemall 商城")
@allure.feature("购物车管理")
@allure.story("参数校验")
@allure.title("缺少购物车数量字段时返回参数错误")
@allure.severity(allure.severity_level.CRITICAL)
def test_add_cart_rejects_missing_number(api_session, available_product):
    response = api_session.post(
        f"{BASE_URL}/wx/cart/add",
        json={
            "goodsId": available_product["goods_id"],
            "productId": available_product["product_id"],
        },
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 401
    assert body["errmsg"] == "参数不对"


@allure.epic("Litemall 商城")
@allure.feature("购物车管理")
@allure.story("数据隔离")
@allure.title("其他用户不能结算或修改当前用户的购物车记录")
@allure.severity(allure.severity_level.BLOCKER)
def test_cart_isolation_between_users(
        api_session,
        secondary_api_session,
        available_product,
        address_factory,
        ):
    product_id = available_product["product_id"]
    peer_session = secondary_api_session["session"]
    peer_address_id, _ = address_factory(peer_session, "第二用户地址")

    add_response = api_session.post(
        f"{BASE_URL}/wx/cart/add",
        json={
            "goodsId": available_product["goods_id"],
            "productId": product_id,
            "number": 1,
        },
        timeout=5,
    )
    assert add_response.json()["errno"] == 0

    try:
        owner_cart = api_session.get(
            f"{BASE_URL}/wx/cart/index",
            timeout=5,
        ).json()["data"]["cartList"]
        cart_item = next(
            item for item in owner_cart
            if item["productId"] == product_id
        )

        with allure.step("第二用户尝试结算第一用户购物车记录"):
            checkout_response = peer_session.get(
                f"{BASE_URL}/wx/cart/checkout",
                params={
                    "cartId": cart_item["id"],
                    "addressId": peer_address_id,
                    "couponId": -1,
                    "userCouponId": -1,
                    "grouponRulesId": 0,
                },
                timeout=5,
            )
            checkout_body = checkout_response.json()
            assert checkout_response.status_code == 200
            assert checkout_body["errno"] == 402

        with allure.step("第二用户尝试修改第一用户购物车记录"):
            update_response = peer_session.post(
                f"{BASE_URL}/wx/cart/update",
                json={
                    "id": cart_item["id"],
                    "goodsId": cart_item["goodsId"],
                    "productId": cart_item["productId"],
                    "number": 2,
                },
                timeout=5,
            )
            update_body = update_response.json()
            assert update_response.status_code == 200
            assert update_body["errno"] == 402

        with allure.step("第一用户的购物车记录仍然存在"):
            owner_cart_after = api_session.get(
                f"{BASE_URL}/wx/cart/index",
                timeout=5,
            ).json()["data"]["cartList"]
            assert any(
                item["id"] == cart_item["id"]
                for item in owner_cart_after
            )
    finally:
        api_session.post(
            f"{BASE_URL}/wx/cart/delete",
            json={"productIds": [product_id]},
            timeout=5,
        )
