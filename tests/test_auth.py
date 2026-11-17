"""Unit tests for password verify, login, and protected routes."""

import bcrypt

from app.auth import verify_password

DEMO_PASSWORD = "changeme"


def test_verify_password_success(password_hash):
    assert verify_password(DEMO_PASSWORD, password_hash) is True


def test_verify_password_failure(password_hash):
    assert verify_password("wrong-password", password_hash) is False
    assert verify_password("", password_hash) is False
    assert verify_password(DEMO_PASSWORD, "") is False
    assert verify_password(DEMO_PASSWORD, "not-a-valid-hash") is False


def test_verify_password_rejects_wrong_hash_algorithm():
    # Malformed / non-bcrypt material should not raise; just fail closed.
    assert verify_password("anything", "$invalid$hash") is False


def test_login_success(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": DEMO_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]
    # Session cookie established
    with client.session_transaction() as sess:
        assert sess.get("username") == "admin"


def test_login_failure_wrong_password(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "nope"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data
    with client.session_transaction() as sess:
        assert sess.get("username") is None


def test_login_failure_wrong_username(client, password_hash):
    # Confirm fixture hash is real bcrypt so the failure path still exercises checkpw.
    assert password_hash.startswith("$2")
    response = client.post(
        "/login",
        data={"username": "notadmin", "password": DEMO_PASSWORD},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data
    with client.session_transaction() as sess:
        assert sess.get("username") is None


def test_dashboard_redirects_when_anonymous(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_ok_when_authenticated(client):
    client.post("/login", data={"username": "admin", "password": DEMO_PASSWORD})
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_logout_clears_session(client):
    client.post("/login", data={"username": "admin", "password": DEMO_PASSWORD})
    response = client.post("/logout", follow_redirects=False)
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess.get("username") is None
    # Protected again
    denied = client.get("/dashboard", follow_redirects=False)
    assert denied.status_code == 302
    assert "/login" in denied.headers["Location"]


def test_bcrypt_hash_roundtrip_independent():
    raw = b"another-secret"
    digest = bcrypt.hashpw(raw, bcrypt.gensalt(rounds=4))
    assert bcrypt.checkpw(raw, digest)
    assert not bcrypt.checkpw(b"nope", digest)
