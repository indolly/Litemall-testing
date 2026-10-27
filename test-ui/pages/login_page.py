import re

from playwright.sync_api import expect

from pages.base_page import BasePage


class LoginPage(BasePage):
    @property
    def username_input(self):
        return self.page.locator("input[name='user']")

    @property
    def password_input(self):
        return self.page.locator("input[name='password']")

    @property
    def login_button(self):
        return self.page.get_by_role("button", name="登录", exact=True)

    @property
    def error_message(self):
        return self.page.locator(".van-toast__text")

    def open(self) -> None:
        super().open("/login")

    def login(self, username: str, password: str) -> None:
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def assert_login_succeeded(self, username: str) -> None:
        expect(self.page).to_have_url(re.compile(r"/#/user/?$"))
        expect(self.page.get_by_text(username, exact=True)).to_be_visible()

    def assert_login_failed(self) -> None:
        expect(self.page).to_have_url(re.compile(r"/#/login/?$"))
        expect(self.error_message).to_contain_text("账号密码不对")
