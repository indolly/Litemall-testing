import json
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parents[1] / "test_config.local.json"

if not CONFIG_PATH.exists():
    raise RuntimeError(
        "缺少本机测试配置。请把 "
        "test-automation/test_config.example.json 复制为 "
        "test-automation/test_config.local.json，并填写自己的测试数据。"
    )

with CONFIG_PATH.open(encoding="utf-8") as config_file:
    CONFIG = json.load(config_file)

BASE_URL = CONFIG["base_url"].rstrip("/")
TEST_USERNAME = CONFIG["test_user"]["username"]
TEST_PASSWORD = CONFIG["test_user"]["password"]
EXPECTED_NICKNAME = CONFIG["test_user"].get(
    "expected_nickname",
    TEST_USERNAME,
)
DATABASE_CONFIG = CONFIG["database"]
