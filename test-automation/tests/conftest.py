import platform
import sys
import uuid
from pathlib import Path

import allure
import pytest
import requests
import pymysql

from settings import (
    BASE_URL,
    DATABASE_CONFIG,
    TEST_PASSWORD,
    TEST_USERNAME,
)

DB_CONFIG={
    "host":DATABASE_CONFIG["host"],
    "port":DATABASE_CONFIG["port"],
    "user":DATABASE_CONFIG["user"],
    "password":DATABASE_CONFIG["password"],
    "database":DATABASE_CONFIG["database"],
    "charset":"utf8mb4",  #让每次查询读取当前已提交的数据

    #查询结果以字典形式返回，后面可以通过字段名取值
    "cursorclass":pymysql.cursors.DictCursor,
    "autocommit":True,
}
@pytest.fixture
def db_connection():
    connection = pymysql.connect(**DB_CONFIG)

    try:
        #yield把连接交给测试函数使用
        yield connection
    finally:
        #无论测试成功或失败，都关闭数据库连接
        connection.close()

@pytest.fixture
def api_session():
    with requests.Session() as session:
        login_response=session.post(
            f"{BASE_URL}/wx/auth/login",
            json={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
            },
            timeout=5,
        )
        login_body=login_response.json()

        assert login_response.status_code == 200
        assert login_body["errno"]==0
        assert login_body["data"]["token"]

        session.headers.update(
            {
                "X-Litemall-Token":login_body["data"]["token"],
            }
        )

        yield session


@pytest.fixture
def secondary_api_session(db_connection):
    """创建一个一次性的第二用户，用于验证跨用户数据隔离。

    临时用户复制主测试账号的密码哈希，因此可以使用同一个本机测试密码
    登录；teardown 按临时 user_id 清理其订单、购物车、地址和用户记录。
    """
    suffix = uuid.uuid4().hex[:10]
    username = f"pytest_peer_{suffix}"
    nickname = f"权限测试用户_{suffix}"
    mobile = f"18{int(suffix, 16) % 1_000_000_000:09d}"

    with db_connection.cursor() as cursor:
        inserted = cursor.execute(
            """
            INSERT INTO litemall_user (
                username, password, gender, birthday,
                last_login_time, last_login_ip, user_level,
                nickname, mobile, avatar, weixin_openid,
                session_key, status, add_time, update_time, deleted
            )
            SELECT
                %s, password, gender, birthday,
                NOW(), '127.0.0.1', user_level,
                %s, %s, avatar, '',
                '', status, NOW(), NOW(), 0
            FROM litemall_user
            WHERE username = %s AND deleted = 0
            LIMIT 1
            """,
            (username, nickname, mobile, TEST_USERNAME),
        )
        assert inserted == 1, "没有找到主测试账号，无法创建临时第二用户"
        user_id = cursor.lastrowid

    try:
        with requests.Session() as session:
            login_response = session.post(
                f"{BASE_URL}/wx/auth/login",
                json={
                    "username": username,
                    "password": TEST_PASSWORD,
                },
                timeout=5,
            )
            login_body = login_response.json()

            assert login_response.status_code == 200
            assert login_body["errno"] == 0
            assert login_body["data"]["token"]

            session.headers.update(
                {"X-Litemall-Token": login_body["data"]["token"]}
            )
            yield {
                "session": session,
                "user_id": user_id,
                "username": username,
            }
    finally:
        # 只清理由本 fixture 创建的临时 user_id，避免影响真实测试账号。
        with db_connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM litemall_order_goods
                WHERE order_id IN (
                    SELECT id FROM litemall_order WHERE user_id = %s
                )
                """,
                (user_id,),
            )
            cursor.execute(
                "DELETE FROM litemall_order WHERE user_id = %s",
                (user_id,),
            )
            cursor.execute(
                "DELETE FROM litemall_cart WHERE user_id = %s",
                (user_id,),
            )
            cursor.execute(
                "DELETE FROM litemall_address WHERE user_id = %s",
                (user_id,),
            )
            cursor.execute(
                "DELETE FROM litemall_coupon_user WHERE user_id = %s",
                (user_id,),
            )
            cursor.execute(
                "DELETE FROM litemall_user WHERE id = %s",
                (user_id,),
            )


@pytest.fixture
def available_product(api_session):
    """返回一个库存大于0的测试SKU，供购物车边界用例复用。"""
    goods_id = 1110017
    response = api_session.get(
        f"{BASE_URL}/wx/goods/detail",
        params={"id": goods_id},
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 0

    product = next(
        (
            item
            for item in body["data"]["productList"]
            if item["number"] > 0
        ),
        None,
    )
    assert product is not None, "测试商品没有可用库存"
    return {
        "goods_id": goods_id,
        "product_id": product["id"],
        "stock": product["number"],
    }


@pytest.fixture
def address_factory(db_connection):
    """通过接口创建地址，并在用例结束后按ID物理清理测试记录。"""
    created_ids = []

    def create(session, label="接口自动化地址"):
        payload = {
            "name": label,
            "tel": "13800138000",
            "province": "北京市",
            "city": "北京市",
            "county": "东城区",
            "areaCode": "110101",
            "addressDetail": "测试路1号（自动化数据）",
            "postalCode": "100000",
            "isDefault": False,
        }
        response = session.post(
            f"{BASE_URL}/wx/address/save",
            json=payload,
            timeout=5,
        )
        body = response.json()
        assert response.status_code == 200
        assert body["errno"] == 0
        address_id = body["data"]
        created_ids.append(address_id)
        return address_id, payload

    yield create

    if created_ids:
        placeholders = ",".join(["%s"] * len(created_ids))
        with db_connection.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM litemall_address WHERE id IN ({placeholders})",
                tuple(created_ids),
            )


#实现订单自动化
@pytest.fixture
def order_context(api_session):
    """
    为订单测试准备独立数据：
    1. 查询一个测试商品的可用规格；
    2. 自动加入购物车；
    3. 查询购物车记录ID；
    4. 查询收货地址ID；
    5. 测试结束后清理仍留在购物车中的测试商品。
    """

    # 使用专门的测试商品，避免影响之前手工加入的1110016
    goods_id = 1110017

    # 查询商品详情，productList中保存具体规格及库存
    detail_response = api_session.get(
        f"{BASE_URL}/wx/goods/detail",
        params={"id": goods_id},
        timeout=5,
    )
    detail_body = detail_response.json()

    assert detail_response.status_code == 200
    assert detail_body["errno"] == 0

    product_list = detail_body["data"]["productList"]

    # next(...) 取得第一条库存大于0的规格；找不到时返回None
    product = next(
        (
            item
            for item in product_list
            if item["number"] > 0
        ),
        None,
    )
    assert product is not None, "测试商品没有可用库存"

    product_id = product["id"]

    # 将该规格加入购物车，数量为1
    add_response = api_session.post(
        f"{BASE_URL}/wx/cart/add",
        json={
            "goodsId": goods_id,
            "productId": product_id,
            "number": 1,
        },
        timeout=5,
    )
    add_body = add_response.json()

    assert add_response.status_code == 200
    assert add_body["errno"] == 0

    # 查询购物车，并找到刚加入的规格
    cart_response = api_session.get(
        f"{BASE_URL}/wx/cart/index",
        timeout=5,
    )
    cart_body = cart_response.json()

    assert cart_response.status_code == 200
    assert cart_body["errno"] == 0

    cart_list = cart_body["data"]["cartList"]
    cart_item = next(
        (
            item
            for item in cart_list
            if item["productId"] == product_id
        ),
        None,
    )
    assert cart_item is not None, "没有找到自动加入的购物车商品"

    # 查询当前测试账号的第一条收货地址
    address_response = api_session.get(
        f"{BASE_URL}/wx/address/list",
        timeout=5,
    )
    address_body = address_response.json()

    assert address_response.status_code == 200
    assert address_body["errno"] == 0

    address_list = address_body["data"]["list"]
    assert address_list, "测试账号没有收货地址"

    # yield前是准备数据；yield的字典会传给测试函数
    yield {
        "goods_id": goods_id,
        "product_id": product_id,
        "cart_id": cart_item["id"],
        "address_id": address_list[0]["id"],
        # 保存下单前库存，后面验证下单扣减和取消恢复
        "stock_before": product["number"],

        # 本次测试购买数量
        "purchase_number": 1,
        #预期写入订单商品表的数据
        "goods_name":cart_item["goodsName"],
        "product_price":cart_item["price"],
    }

    # 测试结束后再次查询购物车
    cleanup_cart_response = api_session.get(
        f"{BASE_URL}/wx/cart/index",
        timeout=5,
    )
    cleanup_cart_body = cleanup_cart_response.json()

    # 如果商品仍在购物车中，则按productId删除
    remaining_product_ids = [
        item["productId"]
        for item in cleanup_cart_body["data"]["cartList"]
        if item["productId"] == product_id
    ]

    if remaining_product_ids:
        api_session.post(
            f"{BASE_URL}/wx/cart/delete",
            json={"productIds": remaining_product_ids},
            timeout=5,
        )

def pytest_sessionfinish(session, exitstatus):
    """
    全部测试执行结束后，自动向 Allure 原始结果目录
    写入本次测试的环境信息。
    """

    # 读取命令行中 --alluredir 指定的目录
    allure_results_dir = session.config.getoption("--alluredir")

    # 如果本次没有要求生成 Allure 结果，就不创建环境文件
    if not allure_results_dir:
        return

    results_path = Path(allure_results_dir)
    results_path.mkdir(parents=True, exist_ok=True)

    # 环境信息中不能写密码、token 等敏感数据
    environment = {
        "Project": "Litemall",
        "Test.Environment": "Local Docker",
        "API.BaseURL": BASE_URL,
        "Operating.System": platform.system(),
        "Python.Version": sys.version.split()[0],
        "Pytest.Version": pytest.__version__,
        "Requests.Version": requests.__version__,
        "Database": "MySQL 5.7.44",
        "Database.Address": (
            f"{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}"
        ),
        "Report.Tool": "Allure 2.45.0",
    }

    environment_content = "\n".join(
        f"{key}={value}"
        for key, value in environment.items()
    )

    environment_file = results_path / "environment.properties"
    environment_file.write_text(
        environment_content,
        encoding="utf-8",
    )

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    每个测试阶段结束后生成测试报告。

    如果测试函数执行失败，则把失败用例名称和错误堆栈
    自动保存到 Allure 报告附件中。
    """

    # 先让其他 Pytest 插件完成本次测试结果的生成
    outcome = yield
    report = outcome.get_result()

    # setup、call、teardown 都会触发该钩子；
    # 这里只处理测试函数正文 call 阶段的失败
    if report.when != "call" or not report.failed:
        return

    failure_information = (
        f"用例标识：{item.nodeid}\n"
        f"失败阶段：{report.when}\n"
        f"失败结果：{report.outcome}\n\n"
        f"错误堆栈：\n{report.longreprtext}"
    )

    allure.attach(
        failure_information,
        name="自动收集的失败信息",
        attachment_type=allure.attachment_type.TEXT,
    )
