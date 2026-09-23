from decimal import Decimal

import allure

from settings import BASE_URL


@allure.epic("Litemall 商城")
@allure.feature("订单管理")
@allure.story("订单结算")
@allure.title("订单结算金额及商品信息计算正确")
@allure.severity(allure.severity_level.CRITICAL)

def test_order_checkout_success(api_session, order_context):

    with allure.step("读取购物车记录和收货地址"):
        # fixture已经准备好购物车记录和地址
        cart_id = order_context["cart_id"]
        address_id = order_context["address_id"]

    with allure.step("调用订单结算预览接口"):
        checkout_response = api_session.get(
            f"{BASE_URL}/wx/cart/checkout",
            params={
                "cartId": cart_id,
                "addressId": address_id,
                "couponId": -1,
                "userCouponId": -1,
                "grouponRulesId": 0,
            },
            timeout=5,
        )

        checkout_body = checkout_response.json()

        # 先验证协议层和业务层结果
        assert checkout_response.status_code == 200
        assert checkout_body["errno"] == 0

    with allure.step("验证结算商品和收货地址"):
        data = checkout_body["data"]
        checked_goods = data["checkedGoodsList"]

        assert data["addressId"] == address_id
        assert checked_goods
        assert checked_goods[0]["id"] == cart_id

    with allure.step("计算并验证订单金额"):
        calculated_goods_total = sum(
            (
                Decimal(str(item["price"])) * item["number"]
                for item in checked_goods
            ),
            Decimal("0"),
        )

        goods_total = Decimal(
            str(data["goodsTotalPrice"])
        )
        freight = Decimal(
            str(data["freightPrice"])
        )
        coupon = Decimal(
            str(data["couponPrice"])
        )
        order_total = Decimal(
            str(data["orderTotalPrice"])
        )
        actual_price = Decimal(
            str(data["actualPrice"])
        )

        assert goods_total == calculated_goods_total
        assert order_total == goods_total + freight - coupon
        assert actual_price == order_total

@allure.epic("Litemall 商城")
@allure.feature("订单管理")
@allure.story("订单状态流转")
@allure.title("订单提交取消删除及数据库状态正确")
@allure.severity(allure.severity_level.CRITICAL)
#订单取消和删除
def test_submit_cancel_and_delete_order(
        api_session,
        order_context,
        db_connection,
        ):
    """
    验证订单完整状态流转：
    提交订单 → 未付款 → 已取消 → 删除。

    finally用于异常清理：
    即使中间断言失败，也尽量取消并删除已创建的测试订单。
    """

    cart_id = order_context["cart_id"]
    address_id = order_context["address_id"]
    product_id = order_context["product_id"]
    goods_id = order_context["goods_id"]
    stock_before = order_context["stock_before"]
    purchase_number = order_context["purchase_number"]

    expected_goods_name = order_context["goods_name"]
    expected_product_price = Decimal(
        str(order_context["product_price"])
    )

    order_id = None
    order_deleted = False

    try:
        # 1. 提交订单
        with allure.step("提交订单并提取动态 orderId"):
            submit_response = api_session.post(
                f"{BASE_URL}/wx/order/submit",
                json={
                    "cartId": cart_id,
                    "addressId": address_id,

                    # -1表示本次订单明确不使用优惠券
                    "couponId": -1,
                    "userCouponId": -1,

                    "message": "pytest自动化测试订单",

                    # 0表示普通订单，不参加团购
                    "grouponRulesId": 0,
                    "grouponLinkId": 0,
                },
                timeout=5,
            )
            submit_body = submit_response.json()

            assert submit_response.status_code == 200
            assert submit_body["errno"] == 0
            assert submit_body["data"]["orderId"]               #存在订单号
            assert submit_body["data"]["payed"] is False        #未付款

            # 保存动态生成的订单ID，后续接口关联使用
            order_id = submit_body["data"]["orderId"]

            #将动态订单ID添加到Allure报告，方便失败时排查
            allure.attach(
                str(order_id),
                name="本次动态 orderId",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("验证订单主表已正确落库"):
            with db_connection.cursor() as cursor:
                cursor.execute(
                    """
                    select
                        id,
                        user_id,
                        order_status,
                        message,
                        deleted
                    from litemall_order
                    where id = %s
                    """,
                    (order_id,),
                )
                db_order = cursor.fetchone() #取第一条

            #接口返回成功后，数据库中必须存在对应的订单
            assert db_order is not None

            #把本次数据库查询结果保存到Allure报告
            allure.attach(
                str(db_order),name="订单主表查询结果",
                attachment_type=allure.attachment_type.TEXT,
            )

            #101表示未付款，0表示订单尚未逻辑删除
            assert db_order["id"]==order_id
            assert db_order["order_status"]==101
            assert db_order["message"]=="pytest自动化测试订单"
            assert db_order["deleted"]==0

        with allure.step("验证下单后SKU库存正确扣减"):
            # 提交订单后重新查询商品详情
            goods_response_after_submit = api_session.get(
                f"{BASE_URL}/wx/goods/detail",
                params={"id": goods_id},
                timeout=5,
            )
            goods_body_after_submit = goods_response_after_submit.json()

            assert goods_response_after_submit.status_code == 200
            assert goods_body_after_submit["errno"] == 0

            # productList 中可能有多个 SKU，需要找到本次购买的 productId
            product_after_submit = next(
                (
                    product
                    for product in goods_body_after_submit["data"]["productList"]
                    if product["id"] == product_id
                ),
                None,

            )
            assert product_after_submit is not None, "提交订单后没有找到对应 SKU"

            #将库存变化保存到allure报告，作为断言证据
            allure.attach(
                (
                    f"product_id={product_id}\n"
                    f"下单前库存={stock_before}\n"
                    f"购买数量={purchase_number}\n"
                    f"下单后库存={product_after_submit['number']}"
                ),
                name="库存扣减结果",
                attachment_type=allure.attachment_type.TEXT,
            )


            # 下单后库存应当减少本次购买数量
            assert product_after_submit["number"] == stock_before - purchase_number


        # 2. 查询刚创建的订单
        with allure.step("查询并验证未付款订单详情"):
            #使用提交订单接口返回的动态order_id 查询本次订单
            detail_response = api_session.get(
                f"{BASE_URL}/wx/order/detail",
                params={"orderId": order_id},
                timeout=5,
            )
            detail_body = detail_response.json()

            assert detail_response.status_code == 200
            assert detail_body["errno"] == 0

            # orderInfo 是订单本身的信息
            # orderGoods 是这张订单包含的商品列表
            order_info = detail_body["data"]["orderInfo"]
            order_goods = detail_body["data"]["orderGoods"]

            assert order_info["id"] == order_id
            assert order_info["message"] == "pytest自动化测试订单"
            assert order_info["orderStatusText"] == "未付款"

            # 未付款订单应该允许用户取消和支付
            assert order_info["handleOption"]["cancel"] is True
            assert order_info["handleOption"]["pay"] is True

            # 订单商品中应该包含fixture自动加入购物车的规格
            assert any(
                item["productId"] == product_id
                for item in order_goods
            )

            #把关键结果保存到allure报告
            allure.attach(
                (
                    f"order_id={order_info['id']}\n"
                    f"订单状态={order_info['orderStatusText']}\n"
                    f"允许取消={order_info['handleOption']['cancel']}\n"
                    f"允许支付={order_info['handleOption']['pay']}\n"
                    f"订单商品数量={len(order_goods)}"
                ),
                name="未付款订单详情",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("验证订单商品子表已正确落库"):
            # 查询订单商品子表，一张订单可能包含多件商品
            with db_connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        order_id,
                        goods_id,
                        product_id,
                        goods_name,
                        price,
                        number,
                        specifications,
                        deleted
                    FROM litemall_order_goods
                    WHERE order_id = %s
                    """,
                    (order_id,),
                )
                db_order_goods = cursor.fetchall()

            # 根据SKU找到本次测试购买的订单商品
            db_order_item = next(
                (
                    item
                    for item in db_order_goods
                    if item["product_id"] == product_id
                ),
                None,
            )

            #先确认数据库中存在对应的订单商品记录
            assert db_order_item is not None,"订单商品子表没有找到对应SKU"

            #把数据库实际查询结果保存到allure
            allure.attach(
                str(db_order_item),
                name="订单商品子表查询结果",
                attachment_type=allure.attachment_type.TEXT,
            )
            assert db_order_item["order_id"] == order_id
            assert db_order_item["goods_id"] == goods_id
            assert db_order_item["product_id"] == product_id
            assert db_order_item["goods_name"] == expected_goods_name
            assert db_order_item["price"] == expected_product_price
            assert db_order_item["number"] == purchase_number
            assert db_order_item["deleted"] == 0

        with allure.step("调用接口取消未付款订单"):
            # 3. 取消订单
            cancel_response = api_session.post(
                f"{BASE_URL}/wx/order/cancel",
                json={"orderId": order_id},
                timeout=5,
            )
            cancel_body = cancel_response.json()

            assert cancel_response.status_code == 200
            assert cancel_body["errno"] == 0

        with allure.step("验证取消后的数据库状态和SKU库存"):
            #查询取消后的数据库状态
            with db_connection.cursor() as cursor:
                cursor.execute(
                    """
                    select order_status,deleted
                    from litemall_order
                    where id=%s
                    """,
                    (order_id,),
                )
                cancelled_db_order=cursor.fetchone()

            assert cancelled_db_order is not None

            #102表示已取消；取消不等于删除，所以deleted为0
            assert cancelled_db_order["order_status"]==102
            assert cancelled_db_order["deleted"]==0

           # 取消订单后重新查询商品详情
            after_cancel_response = api_session.get(
                f"{BASE_URL}/wx/goods/detail",
                params={"id": goods_id},
                timeout=5,
            )
            after_cancel_body = after_cancel_response.json()

            assert after_cancel_response.status_code == 200
            assert after_cancel_body["errno"] == 0

            # 找到本次订单对应的 SKU
            product_after_cancel = next(
                (
                    item
                    for item in after_cancel_body["data"]["productList"]
                    if item["id"] == product_id
                ),
                None,
            )

            assert product_after_cancel is not None, "取消订单后没有找到对应 SKU"

            # 取消订单后，库存应恢复到下单前的数量
            assert product_after_cancel["number"] == stock_before

            allure.attach(
                (
                f"order_id={order_id}\n"
                f"数据库订单状态={cancelled_db_order['order_status']}\n"
                f"数据库删除标记={cancelled_db_order['deleted']}\n"
                f"product_id={product_id}\n"
                f"下单前库存={stock_before}\n"
                f"取消后库存={product_after_cancel['number']}"
                ),
                name="取消订单后的状态和库存",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("言转增已取消订单的状态和可操作权限"):
            # 4. 再次查询，确认订单状态已经改变
            cancelled_detail_response = api_session.get(
                f"{BASE_URL}/wx/order/detail",
                params={"orderId": order_id},
                timeout=5,
            )
            cancelled_detail_body = cancelled_detail_response.json()

            assert cancelled_detail_response.status_code == 200
            assert cancelled_detail_body["errno"] == 0

            cancelled_order_info = cancelled_detail_body["data"]["orderInfo"]
            handle_option = cancelled_order_info["handleOption"]

            # 页面展示的订单状态应为“已取消”
            assert cancelled_order_info["orderStatusText"] == "已取消"

            # 已取消订单不能再次取消或支付，但允许删除
            assert handle_option["cancel"] is False
            assert handle_option["pay"] is False
            assert handle_option["delete"] is True

            allure.attach(
                (
                    f"order_id={order_id}\n"
                    f"订单状态={cancelled_order_info['orderStatusText']}\n"
                    f"允许取消={handle_option['cancel']}\n"
                    f"允许支付={handle_option['pay']}\n"
                    f"允许删除={handle_option['delete']}"
                ),
                name="已取消订单的操作权限",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("删除已取消订单"):
            # 5. 删除测试订单，减少测试数据残留
            delete_response = api_session.post(
                f"{BASE_URL}/wx/order/delete",
                json={"orderId": order_id},
                timeout=5,
            )
            delete_body = delete_response.json()

            assert delete_response.status_code == 200
            assert delete_body["errno"] == 0

            order_deleted = True

            with allure.step("验证数据库逻辑删除和接口不可见"):
                with db_connection.cursor() as cursor:
                    cursor.execute(
                        """
                        select order_status,deleted
                        from litemall_order
                        where id=%s
                        """,
                        (order_id,),
                    )
                    deleted_db_order=cursor.fetchone()

            #litemall采用逻辑删除，数据库记录仍然存在
            assert deleted_db_order is not None
            assert deleted_db_order["order_status"]==102
            assert deleted_db_order["deleted"]==1

            # 6. 删除后再次查询，应该提示订单不存在
            deleted_detail_response = api_session.get(
                f"{BASE_URL}/wx/order/detail",
                params={"orderId": order_id},
                timeout=5,
            )
            deleted_detail_body = deleted_detail_response.json()

            assert deleted_detail_response.status_code == 200
            assert deleted_detail_body["errno"] == 720
            assert deleted_detail_body["errmsg"] == "订单不存在"
            allure.attach(
                (
                    f"order_id={order_id}\n"
                    f"数据库订单状态={deleted_db_order['order_status']}\n"
                    f"数据库删除标记={deleted_db_order['deleted']}\n"
                    f"详情接口HTTP状态码="
                    f"{deleted_detail_response.status_code}\n"
                    f"详情接口业务错误码="
                    f"{deleted_detail_body['errno']}\n"
                    f"详情接口提示="
                    f"{deleted_detail_body['errmsg']}"
                ),
                name="订单逻辑删除验证结果",
                attachment_type=allure.attachment_type.TEXT,
            )

    finally:
        # 如果提交成功但中途断言失败，尽量清理已创建的订单
        if order_id is not None and not order_deleted:
            api_session.post(
                f"{BASE_URL}/wx/order/cancel",
                json={"orderId": order_id},
                timeout=5,
            )
            api_session.post(
                f"{BASE_URL}/wx/order/delete",
                json={"orderId": order_id},
                timeout=5,
            )
