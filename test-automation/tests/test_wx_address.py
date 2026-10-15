import allure
import pytest
import requests

from settings import BASE_URL


@allure.epic("Litemall 商城")
@allure.feature("收货地址")
@allure.story("地址生命周期")
@allure.title("地址新增查询修改删除及数据库状态正确")
@allure.severity(allure.severity_level.CRITICAL)
def test_address_create_update_delete(
        api_session,
        address_factory,
        db_connection,
        ):
    address_id, payload = address_factory(api_session, "地址CRUD测试")

    with allure.step("查询刚创建的地址"):
        detail_response = api_session.get(
            f"{BASE_URL}/wx/address/detail",
            params={"id": address_id},
            timeout=5,
        )
        detail_body = detail_response.json()
        assert detail_response.status_code == 200
        assert detail_body["errno"] == 0
        assert detail_body["data"]["id"] == address_id
        assert detail_body["data"]["name"] == payload["name"]

    with allure.step("修改收货人和详细地址"):
        updated_payload = {
            **payload,
            "id": address_id,
            "name": "地址修改后",
            "addressDetail": "测试路2号（已修改）",
        }
        update_response = api_session.post(
            f"{BASE_URL}/wx/address/save",
            json=updated_payload,
            timeout=5,
        )
        update_body = update_response.json()
        assert update_response.status_code == 200
        assert update_body["errno"] == 0
        assert update_body["data"] == address_id

        updated_detail = api_session.get(
            f"{BASE_URL}/wx/address/detail",
            params={"id": address_id},
            timeout=5,
        ).json()
        assert updated_detail["errno"] == 0
        assert updated_detail["data"]["name"] == "地址修改后"
        assert updated_detail["data"]["addressDetail"] == "测试路2号（已修改）"

    with allure.step("删除地址并验证逻辑删除"):
        delete_response = api_session.post(
            f"{BASE_URL}/wx/address/delete",
            json={"id": address_id},
            timeout=5,
        )
        delete_body = delete_response.json()
        assert delete_response.status_code == 200
        assert delete_body["errno"] == 0

        with db_connection.cursor() as cursor:
            cursor.execute(
                "SELECT deleted FROM litemall_address WHERE id = %s",
                (address_id,),
            )
            row = cursor.fetchone()
        assert row is not None
        assert row["deleted"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("tel", "12345"),
        ("areaCode", ""),
        ("addressDetail", ""),
    ],
    ids=["empty_name", "invalid_mobile", "empty_area_code", "empty_detail"],
)
@allure.epic("Litemall 商城")
@allure.feature("收货地址")
@allure.story("参数校验")
@allure.title("非法地址字段被拒绝：{param_id}")
@allure.severity(allure.severity_level.NORMAL)
def test_address_rejects_invalid_field(api_session, field, value):
    payload = {
        "name": "地址参数测试",
        "tel": "13800138000",
        "province": "北京市",
        "city": "北京市",
        "county": "东城区",
        "areaCode": "110101",
        "addressDetail": "测试路3号",
        "postalCode": "100000",
        "isDefault": False,
    }
    payload[field] = value

    response = api_session.post(
        f"{BASE_URL}/wx/address/save",
        json=payload,
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 401
    assert body["errmsg"] == "参数不对"
    assert not body.get("data")


@allure.epic("Litemall 商城")
@allure.feature("收货地址")
@allure.story("访问权限")
@allure.title("未登录用户查询地址列表被拒绝")
@allure.severity(allure.severity_level.CRITICAL)
def test_address_list_without_token():
    response = requests.get(
        f"{BASE_URL}/wx/address/list",
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 501
    assert body["errmsg"] == "请登录"


@allure.epic("Litemall 商城")
@allure.feature("收货地址")
@allure.story("异常查询")
@allure.title("查询不存在的地址返回参数值错误")
@allure.severity(allure.severity_level.NORMAL)
def test_address_detail_nonexistent(api_session):
    response = api_session.get(
        f"{BASE_URL}/wx/address/detail",
        params={"id": 999999999},
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 402
    assert body["errmsg"] == "参数值不对"


@allure.epic("Litemall 商城")
@allure.feature("收货地址")
@allure.story("数据隔离")
@allure.title("其他用户不能查询或删除当前用户的地址")
@allure.severity(allure.severity_level.BLOCKER)
def test_address_isolation_between_users(
        api_session,
        secondary_api_session,
        address_factory,
        ):
    address_id, _ = address_factory(api_session, "跨用户隔离地址")
    peer_session = secondary_api_session["session"]

    with allure.step("第二用户查询第一用户地址"):
        detail_response = peer_session.get(
            f"{BASE_URL}/wx/address/detail",
            params={"id": address_id},
            timeout=5,
        )
        detail_body = detail_response.json()
        assert detail_response.status_code == 200
        assert detail_body["errno"] == 402

    with allure.step("第二用户尝试删除第一用户地址"):
        delete_response = peer_session.post(
            f"{BASE_URL}/wx/address/delete",
            json={"id": address_id},
            timeout=5,
        )
        delete_body = delete_response.json()
        assert delete_response.status_code == 200
        assert delete_body["errno"] == 402

    with allure.step("第一用户仍可查询该地址"):
        owner_response = api_session.get(
            f"{BASE_URL}/wx/address/detail",
            params={"id": address_id},
            timeout=5,
        )
        owner_body = owner_response.json()
        assert owner_response.status_code == 200
        assert owner_body["errno"] == 0
        assert owner_body["data"]["id"] == address_id
