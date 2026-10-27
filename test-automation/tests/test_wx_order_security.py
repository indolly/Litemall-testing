import allure
import pytest
import requests

from settings import BASE_URL, TEST_USERNAME


pytestmark = pytest.mark.security


def build_submit_payload(order_context, address_id=None):
    return {
        "cartId": order_context["cart_id"],
        "addressId": (
            order_context["address_id"]
            if address_id is None
            else address_id
        ),
        "couponId": -1,
        "userCouponId": -1,
        "message": "pytest异常与权限测试订单",
        "grouponRulesId": 0,
        "grouponLinkId": 0,
    }


def cleanup_order(session, order_id):
    if not order_id:
        return
    session.post(
        f"{BASE_URL}/wx/order/cancel",
        json={"orderId": order_id},
        timeout=5,
    )
    session.post(
        f"{BASE_URL}/wx/order/delete",
        json={"orderId": order_id},
        timeout=5,
    )


@allure.epic("Litemall 商城")
@allure.feature("订单管理")
@allure.story("访问权限")
@allure.title("未登录用户查询订单详情被拒绝")
@allure.severity(allure.severity_level.CRITICAL)
def test_order_detail_without_token():
    response = requests.get(
        f"{BASE_URL}/wx/order/detail",
        params={"orderId": 1},
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 501
    assert body["errmsg"] == "请登录"


@allure.epic("Litemall 商城")
@allure.feature("订单管理")
@allure.story("异常查询")
@allure.title("查询不存在的订单返回订单不存在")
@allure.severity(allure.severity_level.NORMAL)
def test_order_detail_nonexistent(api_session):
    response = api_session.get(
        f"{BASE_URL}/wx/order/detail",
        params={"orderId": 999999999},
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 720
    assert body["errmsg"] == "订单不存在"


@allure.epic("Litemall 商城")
@allure.feature("订单管理")
@allure.story("参数校验")
@allure.title("提交订单缺少地址ID时被拒绝且不产生订单")
@allure.severity(allure.severity_level.CRITICAL)
def test_order_submit_rejects_missing_address(
        api_session,
        order_context,
        db_connection,
        ):
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM litemall_order o
            JOIN litemall_user u ON u.id = o.user_id
            WHERE u.username = %s
              AND o.message = 'pytest异常与权限测试订单'
              AND o.deleted = 0
            """,
            (TEST_USERNAME,),
        )
        count_before = cursor.fetchone()["count"]

    payload = build_submit_payload(order_context)
    payload.pop("addressId")
    response = api_session.post(
        f"{BASE_URL}/wx/order/submit",
        json=payload,
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 401
    assert body["errmsg"] == "参数不对"

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM litemall_order o
            JOIN litemall_user u ON u.id = o.user_id
            WHERE u.username = %s
              AND o.message = 'pytest异常与权限测试订单'
              AND o.deleted = 0
            """,
            (TEST_USERNAME,),
        )
        count_after = cursor.fetchone()["count"]
    assert count_after == count_before


@allure.epic("Litemall 商城")
@allure.feature("订单管理")
@allure.story("数据隔离")
@allure.title("其他用户不能查询当前用户的订单")
@allure.severity(allure.severity_level.BLOCKER)
def test_order_detail_isolation_between_users(
        api_session,
        secondary_api_session,
        order_context,
        ):
    order_id = None
    payload = build_submit_payload(order_context)
    try:
        submit_response = api_session.post(
            f"{BASE_URL}/wx/order/submit",
            json=payload,
            timeout=5,
        )
        submit_body = submit_response.json()
        assert submit_response.status_code == 200
        assert submit_body["errno"] == 0
        order_id = submit_body["data"]["orderId"]

        peer_response = secondary_api_session["session"].get(
            f"{BASE_URL}/wx/order/detail",
            params={"orderId": order_id},
            timeout=5,
        )
        peer_body = peer_response.json()

        assert peer_response.status_code == 200
        assert peer_body["errno"] == 720
        assert peer_body["errmsg"] == "订单不存在"
    finally:
        cleanup_order(api_session, order_id)


@pytest.mark.xfail(
    strict=True,
    reason="已知缺陷：同一cartId重复提交会再次创建订单并重复扣减库存",
)
@allure.epic("Litemall 商城")
@allure.feature("订单管理")
@allure.story("重复提交")
@allure.title("同一购物车重复提交时返回明确业务错误")
@allure.severity(allure.severity_level.BLOCKER)
def test_order_duplicate_submit_is_rejected(api_session, order_context):
    created_order_ids = []
    payload = build_submit_payload(order_context)
    try:
        first_response = api_session.post(
            f"{BASE_URL}/wx/order/submit",
            json=payload,
            timeout=5,
        )
        first_body = first_response.json()
        assert first_body["errno"] == 0
        created_order_ids.append(first_body["data"]["orderId"])

        second_response = api_session.post(
            f"{BASE_URL}/wx/order/submit",
            json=payload,
            timeout=5,
        )
        second_body = second_response.json()
        if second_body.get("errno") == 0:
            created_order_ids.append(second_body["data"]["orderId"])

        assert second_response.status_code == 200
        assert second_body["errno"] in {401, 402, 721, 722}
        assert second_body["errno"] != 502
    finally:
        for created_order_id in reversed(created_order_ids):
            cleanup_order(api_session, created_order_id)


@pytest.mark.xfail(
    strict=True,
    reason="已知缺陷：订单提交按cartId查询时未校验购物车所属用户",
)
@allure.epic("Litemall 商城")
@allure.feature("订单管理")
@allure.story("数据隔离")
@allure.title("其他用户不能提交当前用户的购物车")
@allure.severity(allure.severity_level.BLOCKER)
def test_order_submit_rejects_another_users_cart(
        secondary_api_session,
        order_context,
        address_factory,
        ):
    peer_session = secondary_api_session["session"]
    peer_address_id, _ = address_factory(peer_session, "越权订单测试地址")
    malicious_order_id = None
    payload = build_submit_payload(
        order_context,
        address_id=peer_address_id,
    )

    try:
        response = peer_session.post(
            f"{BASE_URL}/wx/order/submit",
            json=payload,
            timeout=5,
        )
        body = response.json()
        if body.get("errno") == 0:
            malicious_order_id = body["data"]["orderId"]

        assert response.status_code == 200
        assert body["errno"] in {401, 402, 506, 720, 721, 722}
        assert body["errno"] != 0
    finally:
        cleanup_order(peer_session, malicious_order_id)
