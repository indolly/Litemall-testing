import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """UI 测试的公开默认配置，可通过环境变量覆盖。"""

    web_base_url: str = os.getenv("UI_WEB_BASE_URL", "http://127.0.0.1:6255")
    api_base_url: str = os.getenv("UI_API_BASE_URL", "http://127.0.0.1:8081/wx")
    username: str = os.getenv("UI_USERNAME", "user123")
    password: str = os.getenv("UI_PASSWORD", "user123")
    goods_id: int = int(os.getenv("UI_GOODS_ID", "1110016"))
    product_id: int = int(os.getenv("UI_PRODUCT_ID", "150"))
    goods_name: str = os.getenv("UI_GOODS_NAME", "天然硅胶宠物除毛按摩刷")
    search_keyword: str = os.getenv("UI_SEARCH_KEYWORD", "宠物除毛")
    browser_channel: str = os.getenv("UI_BROWSER_CHANNEL", "chrome")

    def page_url(self, route: str = "/") -> str:
        normalized = route if route.startswith("/") else f"/{route}"
        return f"{self.web_base_url.rstrip('/')}/#{normalized}"


SETTINGS = Settings()
