"""Authentication helpers: bcrypt verify and login_required."""

from __future__ import annotations

import secrets
from functools import wraps

import bcrypt
from flask import current_app, flash, redirect, session, url_for


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True if plain_password matches the bcrypt hash (constant-time via bcrypt)."""
    if not plain_password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def verify_credentials(username: str, password: str) -> bool:
    """
    Verify admin username + password.

    Username compared with secrets.compare_digest; password via bcrypt.checkpw.
    """
    expected_user = current_app.config["ADMIN_USERNAME"]
    password_hash = current_app.config["ADMIN_PASSWORD_HASH"]
    if not expected_user or not password_hash:
        return False

    # Always run bcrypt against the real hash to avoid leaking username validity via timing.
    password_ok = verify_password(password, password_hash)
    username_ok = secrets.compare_digest(username or "", expected_user)
    return bool(username_ok and password_ok)


def login_user(username: str) -> None:
    session.clear()
    session["username"] = username
    session.permanent = False


def logout_user() -> None:
    session.clear()


def current_username() -> str | None:
    return session.get("username")


def is_authenticated() -> bool:
    return bool(current_username())


def login_required(view):
    """Redirect anonymous users to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            flash("Please sign in to continue.", "error")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped
