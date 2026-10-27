import base64
import hashlib
import hmac
import json
import time

import allure
import pytest
import requests

from settings import BASE_URL, TEST_PASSWORD, TEST_USERNAME


pytestmark = pytest.mark.security

FORBIDDEN_RESPONSE_KEYS = {
    "password",
    "sessionkey",
    "weixinopenid",
    "lastloginip",
    "salt",
}
INTERNAL_ERROR_MARKERS = (
    "exception",
    "java.",
    "org.linlinjava",
    "select ",
    "insert ",
    "update ",
    "delete from",
    "traceback",
)


def _base64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def build_expired_token(user_id=1):
    """按被测系统的 JWT 格式构造一个签名正确但已经过期的 Token。"""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "userId": user_id,
        "iss": "LITEMALL",
        "sub": "this is litemall token",
        "aud": ["MINIAPP"],
        "iat": now - 7200,
        "exp": now - 3600,
    }
    encoded_header = _base64url(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    encoded_payload = _base64url(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        b"X-Litemall-Token",
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{encoded_header}.{encoded_payload}.{_base64url(signature)}"


def iter_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key).lower()
            yield from iter_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_keys(item)


def assert_no_internal_details(body):
    serialized = json.dumps(body, ensure_ascii=False).lower()
    assert not any(marker in serialized for marker in INTERNAL_ERROR_MARKERS)


def build_order_payload(order_context, address_id=None):
    return {
        "cartId": order_context["cart_id"],
        "addressId": (
            order_context["address_id"]
            if address_id is None
            else address_id
        ),
        "couponId": -1,
        "userCouponId": -1,
        "message": "pytest基础安全测试订单",
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


@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("get", "/wx/address/list", {}),
        ("get", "/wx/cart/index", {}),
        ("get", "/wx/order/list", {}),
        ("get", "/wx/auth/info", {}),
        ("post", "/wx/order/cancel", {"json": {"orderId": 1}}),
    ],
    ids=[
        "address_list",
        "cart_index",
        "order_list",
        "user_info",
        "order_cancel",
    ],
)
@allure.epic("Litemall 商城")
@allure.feature("基础安全")
@allure.story("认证")
@allure.title("未登录访问受保护接口被拒绝：{param_id}")
@allure.severity(allure.severity_level.BLOCKER)
def test_protected_endpoint_rejects_missing_token(method, path, kwargs):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        timeout=5,
        **kwargs,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 501
    assert body["errmsg"] == "请登录"
    assert not body.get("data")
    assert_no_internal_details(body)


@pytest.mark.parametrize(
    "token",
    [
        "invalid_token_123456",
        build_expired_token(),
    ],
    ids=["forged_token", "expired_token"],
)
@allure.epic("Litemall 商城")
@allure.feature("基础安全")
@allure.story("Token 校验")
@allure.title("伪造或过期 Token 被拒绝：{param_id}")
@allure.severity(allure.severity_level.BLOCKER)
def test_protected_endpoint_rejects_invalid_or_expired_token(token):
    response = requests.get(
        f"{BASE_URL}/wx/address/list",
        headers={"X-Litemall-Token": token},
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 501
    assert body["errmsg"] == "请登录"
    assert not body.get("data")
    assert_no_internal_details(body)


@allure.epic("Litemall 商城")
@allure.feature("基础安全")
@allure.story("输入校验")
@allure.title("登录账号字段中的 SQL 风格输入不能绕过认证")
@allure.severity(allure.severity_level.CRITICAL)
def test_login_rejects_sql_style_username():
    response = requests.post(
        f"{BASE_URL}/wx/auth/login",
        json={
            "username": f"{TEST_USERNAME}' OR '1'='1",
            "password": TEST_PASSWORD,
        },
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] != 0
    assert not body.get("data")
    assert_no_internal_details(body)


@allure.epic("Litemall 商城")
@allure.feature("基础安全")
@allure.story("敏感信息")
@allure.title("登录响应不返回密码、会话密钥和内部账号字段")
@allure.severity(allure.severity_level.BLOCKER)
def test_login_response_does_not_expose_sensitive_fields():
    response = requests.post(
        f"{BASE_URL}/wx/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 0
    assert body["data"]["token"]
    assert FORBIDDEN_RESPONSE_KEYS.isdisjoint(set(iter_keys(body)))


@allure.epic("Litemall 商城")
@allure.feature("基础安全")
@allure.story("敏感信息")
@allure.title("用户信息接口只返回必要资料，不泄露认证字段")
@allure.severity(allure.severity_level.CRITICAL)
def test_user_info_response_does_not_expose_authentication_fields(api_session):
    response = api_session.get(f"{BASE_URL}/wx/auth/info", timeout=5)
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 0
    assert set(body["data"]).issubset({"nickName", "avatar", "gender", "mobile"})
    assert FORBIDDEN_RESPONSE_KEYS.isdisjoint(set(iter_keys(body)))


@allure.epic("Litemall 商城")
@allure.feature("基础安全")
@allure.story("对象级授权")
@allure.title("用户不能读取、修改或删除其他用户的地址")
@allure.severity(allure.severity_level.BLOCKER)
def test_address_object_authorization(
        api_session,
        secondary_api_session,
        address_factory,
        ):
    address_id, payload = address_factory(api_session, "地址越权保护原值")
    peer_session = secondary_api_session["session"]

    detail_response = peer_session.get(
        f"{BASE_URL}/wx/address/detail",
        params={"id": address_id},
        timeout=5,
    )
    assert detail_response.json()["errno"] == 402

    tampered_payload = {
        **payload,
        "id": address_id,
        "name": "地址越权篡改值",
        "addressDetail": "其他用户试图覆盖的地址",
    }
    update_response = peer_session.post(
        f"{BASE_URL}/wx/address/save",
        json=tampered_payload,
        timeout=5,
    )
    assert update_response.json()["errno"] == 402

    delete_response = peer_session.post(
        f"{BASE_URL}/wx/address/delete",
        json={"id": address_id},
        timeout=5,
    )
    assert delete_response.json()["errno"] == 402

    owner_body = api_session.get(
        f"{BASE_URL}/wx/address/detail",
        params={"id": address_id},
        timeout=5,
    ).json()
    assert owner_body["errno"] == 0
    assert owner_body["data"]["name"] == "地址越权保护原值"
    assert owner_body["data"]["addressDetail"] == payload["addressDetail"]


@allure.epic("Litemall 商城")
@allure.feature("基础安全")
@allure.story("参数篡改")
@allure.title("创建地址时篡改 userId 不会改变数据归属")
@allure.severity(allure.severity_level.BLOCKER)
def test_address_user_id_tampering_is_ignored(
        api_session,
        secondary_api_session,
        db_connection,
        ):
    address_id = None
    payload = {
        "userId": secondary_api_session["user_id"],
        "name": "userId篡改测试地址",
        "tel": "13800138000",
        "province": "北京市",
        "city": "北京市",
        "county": "东城区",
        "areaCode": "110101",
        "addressDetail": "安全测试路1号",
        "postalCode": "100000",
        "isDefault": False,
    }
    try:
        response = api_session.post(
            f"{BASE_URL}/wx/address/save",
            json=payload,
            timeout=5,
        )
        body = response.json()
        assert body["errno"] == 0
        address_id = body["data"]

        with db_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.user_id, u.username
                FROM litemall_address a
                JOIN litemall_user u ON u.id = a.user_id
                WHERE a.id = %s
                """,
                (address_id,),
            )
            row = cursor.fetchone()

        assert row["username"] == TEST_USERNAME
        assert row["user_id"] != secondary_api_session["user_id"]
    finally:
        if address_id:
            api_session.post(
                f"{BASE_URL}/wx/address/delete",
                json={"id": address_id},
                timeout=5,
            )


@allure.epic("Litemall 商城")
@allure.feature("基础安全")
@allure.story("参数篡改")
@allure.title("用户不能使用其他用户的地址提交订单")
@allure.severity(allure.severity_level.BLOCKER)
def test_order_rejects_another_users_address(
        api_session,
        secondary_api_session,
        order_context,
        address_factory,
        ):
    peer_address_id, _ = address_factory(
        secondary_api_session["session"],
        "其他用户订单地址",
    )
    response = api_session.post(
        f"{BASE_URL}/wx/order/submit",
        json=build_order_payload(order_context, address_id=peer_address_id),
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] in {401, 402}
    assert not body.get("data")
    assert_no_internal_details(body)


@allure.epic("Litemall 商城")
@allure.feature("基础安全")
@allure.story("对象级授权")
@allure.title("用户不能查询、取消或删除其他用户的订单")
@allure.severity(allure.severity_level.BLOCKER)
def test_order_object_authorization(
        api_session,
        secondary_api_session,
        order_context,
        db_connection,
        ):
    order_id = None
    peer_session = secondary_api_session["session"]
    try:
        submit_body = api_session.post(
            f"{BASE_URL}/wx/order/submit",
            json=build_order_payload(order_context),
            timeout=5,
        ).json()
        assert submit_body["errno"] == 0
        order_id = submit_body["data"]["orderId"]

        detail_body = peer_session.get(
            f"{BASE_URL}/wx/order/detail",
            params={"orderId": order_id},
            timeout=5,
        ).json()
        assert detail_body["errno"] == 720

        cancel_body = peer_session.post(
            f"{BASE_URL}/wx/order/cancel",
            json={"orderId": order_id},
            timeout=5,
        ).json()
        assert cancel_body["errno"] == 402

        delete_body = peer_session.post(
            f"{BASE_URL}/wx/order/delete",
            json={"orderId": order_id},
            timeout=5,
        ).json()
        assert delete_body["errno"] in {401, 402}

        with db_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT o.user_id, o.order_status, o.deleted, u.username
                FROM litemall_order o
                JOIN litemall_user u ON u.id = o.user_id
                WHERE o.id = %s
                """,
                (order_id,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row["username"] == TEST_USERNAME
        assert row["order_status"] == 101
        assert row["deleted"] == 0
    finally:
        cleanup_order(api_session, order_id)
