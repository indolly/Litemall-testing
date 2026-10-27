from playwright.sync_api import Page

from config.settings import Settings


class BasePage:
    """页面对象的最小公共能力。"""

    def __init__(self, page: Page, settings: Settings):
        self.page = page
        self.settings = settings

    def open(self, route: str = "/") -> None:
        self.page.goto(self.settings.page_url(route), wait_until="domcontentloaded")
