"""Shared pytest fixtures."""

import bcrypt
import pytest

from app import create_app
from app.config import TestConfig

DEMO_PASSWORD = "changeme"


@pytest.fixture()
def password_hash():
    return bcrypt.hashpw(DEMO_PASSWORD.encode("utf-8"), bcrypt.gensalt(rounds=4)).decode()


@pytest.fixture()
def app(password_hash, tmp_path):
    inventory_file = tmp_path / "servers.json"

    class LocalTestConfig(TestConfig):
        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD_HASH = password_hash
        INVENTORY_PATH = str(inventory_file)
        CPU_ALERT_THRESHOLD = 80.0
        MEMORY_ALERT_THRESHOLD = 80.0

    application = create_app(LocalTestConfig)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    client.post("/login", data={"username": "admin", "password": DEMO_PASSWORD})
    return client
