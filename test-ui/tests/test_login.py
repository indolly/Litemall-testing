from pages.login_page import LoginPage


def test_login_success(page, settings):
    login = LoginPage(page, settings)
    login.open()
    login.login(settings.username, settings.password)
    login.assert_login_succeeded(settings.username)


def test_login_failure_with_wrong_password(page, settings):
    login = LoginPage(page, settings)
    login.open()
    login.login(settings.username, "wrong-password")
    login.assert_login_failed()
