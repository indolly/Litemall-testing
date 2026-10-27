from pages.base_page import BasePage


class HomePage(BasePage):
    @property
    def search_entry(self):
        return self.page.locator("input[placeholder='点击前往搜索']")

    def open(self) -> None:
        super().open("/")

    def go_to_search(self) -> None:
        self.search_entry.click()
