"""Application routes: public home, auth, and protected dashboard."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import (
    is_authenticated,
    login_required,
    login_user,
    logout_user,
    verify_credentials,
)

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    """Public landing page — no authentication required."""
    return render_template("home.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if is_authenticated():
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if verify_credentials(username, password):
            login_user(username)
            flash("Signed in successfully.", "ok")
            next_url = request.args.get("next") or url_for("main.dashboard")
            return redirect(next_url)
        flash("Invalid username or password.", "error")

    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Signed out.", "ok")
    return redirect(url_for("main.home"))


@bp.route("/dashboard")
@login_required
def dashboard():
    """Placeholder dashboard — requires a signed-in session."""
    return render_template("dashboard.html")
