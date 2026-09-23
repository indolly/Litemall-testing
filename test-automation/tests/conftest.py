import platform
import sys
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
