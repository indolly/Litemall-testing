import requests
import pytest
import allure

from settings import (
    BASE_URL,
    EXPECTED_NICKNAME,
    TEST_PASSWORD,
    TEST_USERNAME,
)


@allure.epic("Litemall 商城")
@allure.feature("用户认证")
@allure.story("登录")
@allure.title("正确账号密码登录成功")
@allure.severity(allure.severity_level.CRITICAL)
#登录
def test_login_success():
    # Arrange：准备测试数据
    payload = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
    }

    # Act：发送请求
    response = requests.post(
        f"{BASE_URL}/wx/auth/login",
        json=payload,
        timeout=5,
    )
    body = response.json()

    # Assert：验证结果
    assert response.status_code == 200
    assert body["errno"] == 0
    assert body["errmsg"] == "成功"
    assert body["data"]["token"]
    assert body["data"]["userInfo"]["nickName"] == EXPECTED_NICKNAME

#错误密码
@allure.epic("Litemall 商城")
@allure.feature("用户认证")
@allure.story("登录异常")
@allure.title("错误密码登录被拒绝")
@allure.severity(allure.severity_level.CRITICAL)
def test_login_wrong_password():
    # Arrange
    payload = {
        "username": TEST_USERNAME,
        "password": f"{TEST_PASSWORD}_invalid",
    }

    # Act
    response = requests.post(
        f"{BASE_URL}/wx/auth/login",
        json=payload,
        timeout=5,
    )
    body = response.json()

    # Assert
    assert response.status_code == 200
    assert body["errno"] == 700
    assert body["errmsg"] == "账号密码不对"
    assert not body.get("data")


@pytest.mark.parametrize(
    "username,password",
    [
        ("", TEST_PASSWORD),
        ("not_exist_test_account", TEST_PASSWORD),
    ],
    ids=[
        "empty_username",
        "nonexistent_username",
    ],
)

@allure.epic("Litemall 商城")
@allure.feature("用户认证")
@allure.story("登录异常")
@allure.title("非法账号登录被拒绝：{param_id}")
@allure.severity(allure.severity_level.NORMAL)
def test_login_rejects_invalid_account(username, password):
    allure.dynamic.parameter(
        "password",
        "******",
        mode=allure.parameter_mode.MASKED
    )
    payload={
        "username":username,
        "password":password,
    }

    response=requests.post(
        f"{BASE_URL}/wx/auth/login",
        json=payload,
        timeout=5,
    )
    body=response.json()

    assert response.status_code==200
    assert body["errno"]==700
    assert body["errmsg"]
    assert not body.get("data")
