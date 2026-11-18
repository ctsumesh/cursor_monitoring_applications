# Server Monitor

Local Flask demo for viewing Linux server metrics (CPU, memory, network, listening ports) over SSH without logging into each host for inspection.

## Requirements

- Python 3.10+ recommended
- SSH access to lab/local Linux hosts you own or are authorized to monitor

## Setup

```bash
cd monitoring_application
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Config and secrets

1. Copy the example auth config:

   ```bash
   cp config.example.json config.json
   ```

2. Set a session secret (required):

   ```bash
   export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
   ```

   See `.env.example`. Do **not** commit `.env` or `config.json`.

3. Admin login uses username + **bcrypt** hash from the config file (no plaintext password in the repo).

#### Generate a bcrypt password hash

```bash
source .venv/bin/activate
python - <<'PY'
import bcrypt, getpass
password = getpass.getpass("Password: ").encode("utf-8")
print(bcrypt.hashpw(password, bcrypt.gensalt(rounds=12)).decode())
PY
```

Put the printed hash into `config.json` as `admin_password_hash`.

The committed `config.example.json` hash matches the demo password `changeme` (local demo only).

## Run (localhost)

```bash
source .venv/bin/activate
export FLASK_SECRET_KEY="${FLASK_SECRET_KEY:-dev-local-only-change-me}"
flask --app app run --host 127.0.0.1 --port 5123
```

Open [http://127.0.0.1:5123](http://127.0.0.1:5123). Sign-in: [http://127.0.0.1:5123/login](http://127.0.0.1:5123/login).

### Main user flow

1. Sign in as `admin`
2. **Servers → Add server** (host, SSH port, username, password or key path)
3. Open the server (or Dashboard) and click **Refresh**
4. View CPU, memory, network rx/tx + connection count, and listening ports

### How to add a server

1. Sign in → **Servers** → **Add server**
2. Fill name, host (`localhost` / IPv4 / hostname), SSH port (default 22), username
3. Choose auth: password, or absolute/`~/` private key path
4. Save — credentials are stored only in local gitignored `data/servers.json`

## Tests

```bash
source .venv/bin/activate
pytest
```

## CI (GitHub Actions)

On every push and pull request to `main`, GitHub Actions runs a light syntax check and `pytest` on **Python 3.10**.

- Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- CI uses a **dummy** `FLASK_SECRET_KEY` and `config.example.json` only — no real secrets, and no credential artifacts are published.

## Inventory storage

| Item | Detail |
|------|--------|
| File | `data/servers.json` (gitignored) |
| Fields | `name`, `host`, `port`, `username`, `auth_type` (`password`/`key`), `password`, `key_path`, last metrics/error timestamps |

## SSH metrics (read-only)

Allowlisted remote reads only (no free-form shell from the UI):

| Metric | Source |
|--------|--------|
| CPU % | Two samples of `/proc/stat` (`cpu` line) |
| Memory | `/proc/meminfo` |
| Network rx/tx + connections | `/proc/net/dev`, `/proc/net/tcp`, `/proc/net/tcp6` |
| Listening ports | TCP state `0A` (LISTEN) in `/proc/net/tcp{,6}` |

Demo limitation: local/lab hosts you control. Unknown SSH host keys are auto-added for convenience (not for production).

## Alerts

Default thresholds: **CPU ≥ 80%** or **memory ≥ 80%** (after a manual refresh).

Override in `config.json`:

```json
"cpu_alert_threshold": 80,
"memory_alert_threshold": 80
```

Or env: `CPU_ALERT_THRESHOLD`, `MEMORY_ALERT_THRESHOLD`. No email/Slack — dashboard highlight only.

## Project layout

| Path | Role |
|------|------|
| `app/` | Flask package (auth, inventory, SSH, metrics, routes, templates) |
| `config.example.json` | Example admin + alert thresholds (safe to commit) |
| `config.json` | Local overrides (gitignored) |
| `data/servers.json` | Server inventory + last metrics (gitignored) |
| `tests/` | Unit tests (`pytest`) |
| `docs/` | PRD and step-by-step TODO |
| `.github/workflows/ci.yml` | GitHub Actions CI |

## Security notes

- Passwords verified with **bcrypt**; username compare uses `secrets.compare_digest`.
- Session `SECRET_KEY` from `FLASK_SECRET_KEY` or local `config.json` — not committed.
- CSRF on mutating forms (Flask-WTF). Templates escape user fields by default.
- SSH: allowlisted commands only; passwords/keys never logged or shown in the UI after save.
- Metrics UI is read-only; writes are login + inventory CRUD only.
- Do not commit `.env`, `config.json`, `data/servers.json`, or private keys.
- `FLASK_DEBUG` defaults to off.
