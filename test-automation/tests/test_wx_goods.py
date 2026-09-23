import requests
import allure

from settings import BASE_URL

@allure.epic("Litemall 商城")
@allure.feature("商品管理")
@allure.story("商品搜索")
@allure.title("使用有效关键词搜索到相关商品")
@allure.severity(allure.severity_level.NORMAL)
def test_search_existing_goods():
    params={
        "keyword":"宠物除毛",
        "page":1,
        "limit":10,
    }

    response=requests.get(
        f"{BASE_URL}/wx/goods/list",
        params=params,
        timeout=5,
    )
    body=response.json()

    assert response.status_code==200
    assert body["errno"]==0

    goods_list=body["data"]["list"]

    assert len(goods_list)>0
    assert any(
        "宠物除毛" in goods["name"]
        for goods in goods_list
    )
@allure.epic("Litemall 商城")
@allure.feature("商品管理")
@allure.story("商品搜索")
@allure.title("使用不存在的关键词搜索结果为空")
def test_search_nonexistent_goods():
    params = {
        "keyword": "不存在商品123456",
        "page": 1,
        "limit": 10,
    }

    response = requests.get(
        f"{BASE_URL}/wx/goods/list",
        params=params,
        timeout=5,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["errno"] == 0
    assert body["data"]["total"] == 0
    assert body["data"]["list"] == []
