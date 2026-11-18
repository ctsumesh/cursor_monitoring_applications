"""Unit tests for server inventory CRUD validation."""

import pytest

from app.inventory import InventoryError, ServerInventory, validate_server_payload


def test_reject_empty_host():
    with pytest.raises(InventoryError):
        validate_server_payload(
            {
                "name": "a",
                "host": "",
                "port": 22,
                "username": "u",
                "auth_type": "password",
                "password": "x",
            }
        )


def test_reject_invalid_port():
    with pytest.raises(InventoryError):
        validate_server_payload(
            {
                "name": "a",
                "host": "localhost",
                "port": 70000,
                "username": "u",
                "auth_type": "password",
                "password": "x",
            }
        )


def test_crud_roundtrip(tmp_path):
    inv = ServerInventory(tmp_path / "servers.json")
    server = inv.add(
        {
            "name": "lab",
            "host": "127.0.0.1",
            "port": 22,
            "username": "ubuntu",
            "auth_type": "password",
            "password": "secret",
        }
    )
    assert server["id"]
    assert inv.get(server["id"])["host"] == "127.0.0.1"
    updated = inv.update(server["id"], {"name": "lab-2"})
    assert updated["name"] == "lab-2"
    # blank password keeps existing
    assert updated["password"] == "secret"
    inv.delete(server["id"])
    assert inv.get(server["id"]) is None


def test_inventory_routes_require_login(client):
    assert client.get("/servers").status_code == 302
    assert client.get("/servers/new").status_code == 302


def test_add_server_via_ui(auth_client):
    resp = auth_client.post(
        "/servers/new",
        data={
            "name": "demo",
            "host": "localhost",
            "port": "22",
            "username": "demo",
            "auth_type": "password",
            "password": "pw",
            "key_path": "",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    listed = auth_client.get("/servers")
    assert listed.status_code == 200
    assert b"demo" in listed.data
    assert b"localhost" in listed.data
