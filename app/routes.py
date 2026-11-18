"""Application routes: auth, inventory CRUD, dashboard, metrics (read-only)."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.alerts import evaluate_alerts
from app.auth import (
    is_authenticated,
    login_required,
    login_user,
    logout_user,
    verify_credentials,
)
from app.inventory import InventoryError, ServerInventory
from app.metrics import collect_metrics
from app.ssh_client import SSHError, SSHTarget

bp = Blueprint("main", __name__)


def _inventory() -> ServerInventory:
    return ServerInventory(current_app.config["INVENTORY_PATH"])


def _thresholds() -> tuple[float, float]:
    return (
        float(current_app.config["CPU_ALERT_THRESHOLD"]),
        float(current_app.config["MEMORY_ALERT_THRESHOLD"]),
    )


def _public_server(server: dict) -> dict:
    """Strip secrets before templates (templates also must not print password)."""
    return {
        "id": server.get("id"),
        "name": server.get("name"),
        "host": server.get("host"),
        "port": server.get("port"),
        "username": server.get("username"),
        "auth_type": server.get("auth_type"),
        "key_path": server.get("key_path") or "",
        "has_password": bool(server.get("password")),
        "last_metrics": server.get("last_metrics"),
        "last_error": server.get("last_error"),
        "last_refreshed_at": server.get("last_refreshed_at"),
    }


def _target_from_server(server: dict) -> SSHTarget:
    return SSHTarget(
        host=server["host"],
        port=int(server["port"]),
        username=server["username"],
        auth_type=server.get("auth_type") or "password",
        password=server.get("password") or "",
        key_path=server.get("key_path") or "",
    )


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
    cpu_th, mem_th = _thresholds()
    rows = []
    for server in _inventory().list_servers():
        pub = _public_server(server)
        alerts = evaluate_alerts(
            server.get("last_metrics"),
            cpu_threshold=cpu_th,
            memory_threshold=mem_th,
        )
        pub["alerts"] = alerts
        rows.append(pub)
    return render_template(
        "dashboard.html",
        servers=rows,
        cpu_threshold=cpu_th,
        memory_threshold=mem_th,
    )


@bp.route("/servers")
@login_required
def servers_list():
    servers = [_public_server(s) for s in _inventory().list_servers()]
    return render_template("servers_list.html", servers=servers)


@bp.route("/servers/new", methods=["GET", "POST"])
@login_required
def servers_new():
    if request.method == "POST":
        payload = {
            "name": request.form.get("name"),
            "host": request.form.get("host"),
            "port": request.form.get("port") or 22,
            "username": request.form.get("username"),
            "auth_type": request.form.get("auth_type") or "password",
            "password": request.form.get("password") or "",
            "key_path": request.form.get("key_path") or "",
        }
        try:
            server = _inventory().add(payload)
        except InventoryError as exc:
            flash(str(exc), "error")
            return render_template("server_form.html", mode="new", form=payload), 400
        flash(f"Added server {server['name']}.", "ok")
        return redirect(url_for("main.servers_list"))
    return render_template(
        "server_form.html",
        mode="new",
        form={
            "name": "",
            "host": "",
            "port": 22,
            "username": "",
            "auth_type": "password",
            "password": "",
            "key_path": "",
        },
    )


@bp.route("/servers/<server_id>/edit", methods=["GET", "POST"])
@login_required
def servers_edit(server_id: str):
    inv = _inventory()
    server = inv.get(server_id)
    if not server:
        flash("Server not found.", "error")
        return redirect(url_for("main.servers_list"))

    if request.method == "POST":
        payload = {
            "name": request.form.get("name"),
            "host": request.form.get("host"),
            "port": request.form.get("port") or 22,
            "username": request.form.get("username"),
            "auth_type": request.form.get("auth_type") or server.get("auth_type"),
            "password": request.form.get("password") or "",
            "key_path": request.form.get("key_path")
            if request.form.get("key_path") is not None
            else server.get("key_path"),
        }
        try:
            updated = inv.update(server_id, payload)
        except InventoryError as exc:
            flash(str(exc), "error")
            form = _public_server(server)
            form.update({k: payload.get(k, form.get(k)) for k in payload})
            return render_template("server_form.html", mode="edit", form=form, server_id=server_id), 400
        flash(f"Updated server {updated['name']}.", "ok")
        return redirect(url_for("main.server_detail", server_id=server_id))

    return render_template(
        "server_form.html",
        mode="edit",
        form=_public_server(server),
        server_id=server_id,
    )


@bp.route("/servers/<server_id>/delete", methods=["POST"])
@login_required
def servers_delete(server_id: str):
    try:
        _inventory().delete(server_id)
        flash("Server deleted.", "ok")
    except InventoryError as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.servers_list"))


@bp.route("/servers/<server_id>")
@login_required
def server_detail(server_id: str):
    server = _inventory().get(server_id)
    if not server:
        flash("Server not found.", "error")
        return redirect(url_for("main.servers_list"))
    cpu_th, mem_th = _thresholds()
    pub = _public_server(server)
    pub["alerts"] = evaluate_alerts(
        server.get("last_metrics"),
        cpu_threshold=cpu_th,
        memory_threshold=mem_th,
    )
    return render_template("server_detail.html", server=pub)


@bp.route("/servers/<server_id>/refresh", methods=["POST"])
@login_required
def server_refresh(server_id: str):
    inv = _inventory()
    server = inv.get(server_id)
    if not server:
        flash("Server not found.", "error")
        return redirect(url_for("main.servers_list"))

    now = datetime.now(timezone.utc).isoformat()
    try:
        metrics = collect_metrics(_target_from_server(server))
        inv.save_metrics(server_id, metrics, None, now)
        flash("Metrics refreshed.", "ok")
    except (SSHError, KeyError, OSError) as exc:
        # Never include password/key material in flash
        msg = str(exc) if isinstance(exc, SSHError) else "Refresh failed"
        inv.save_metrics(server_id, server.get("last_metrics"), msg, now)
        flash(msg, "error")

    next_page = request.form.get("next") or url_for("main.server_detail", server_id=server_id)
    if next_page.startswith("/"):
        return redirect(next_page)
    return redirect(url_for("main.server_detail", server_id=server_id))


@bp.route("/dashboard/refresh-all", methods=["POST"])
@login_required
def dashboard_refresh_all():
    inv = _inventory()
    ok = 0
    fail = 0
    for server in inv.list_servers():
        now = datetime.now(timezone.utc).isoformat()
        try:
            metrics = collect_metrics(_target_from_server(server))
            inv.save_metrics(server["id"], metrics, None, now)
            ok += 1
        except (SSHError, KeyError, OSError) as exc:
            msg = str(exc) if isinstance(exc, SSHError) else "Refresh failed"
            inv.save_metrics(server["id"], server.get("last_metrics"), msg, now)
            fail += 1
    if fail and ok:
        flash(f"Refreshed {ok} server(s); {fail} failed.", "error")
    elif fail:
        flash(f"Refresh failed for {fail} server(s).", "error")
    else:
        flash(f"Refreshed {ok} server(s).", "ok")
    return redirect(url_for("main.dashboard"))
