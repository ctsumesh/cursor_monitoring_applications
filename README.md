# Server Monitor

Local Flask demo for viewing Linux server metrics (CPU, memory, network, listening ports) over SSH without logging into each host for inspection.

## Requirements

- Python 3.10+ recommended

## Setup

```bash
cd monitoring_application
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Config and secrets

1. Copy the example auth config (optional if you are fine using the example file as-is):

   ```bash
   cp config.example.json config.json
   ```

2. Set a session secret (required). Either export it or add `"secret_key"` to `config.json`:

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

Put the printed hash into `config.json` as `admin_password_hash` (and set `admin_username` if needed).

The committed `config.example.json` hash matches the demo password `changeme` (local demo only — change it if this machine is shared).

## Run (localhost)

```bash
source .venv/bin/activate
export FLASK_SECRET_KEY="${FLASK_SECRET_KEY:-dev-local-only-change-me}"
flask --app app run --host 127.0.0.1 --port 5123
```

Open [http://127.0.0.1:5123](http://127.0.0.1:5123). If that port is busy, pick another (e.g. `--port 5130`).

- Home is public
- Sign in at `/login` as `admin`
- `/dashboard` requires a session

## Tests

```bash
source .venv/bin/activate
pytest
```

## Project layout

| Path | Role |
|------|------|
| `app/` | Flask package (factory, auth, routes, templates, static) |
| `config.example.json` | Example admin username + bcrypt hash (safe to commit) |
| `config.json` | Local overrides (gitignored) |
| `tests/` | Unit tests (`pytest`) |
| `docs/` | PRD and step-by-step TODO |
| `.env.example` | Env var template (do not commit `.env`) |

## Security notes

- Passwords are verified with **bcrypt** only (`bcrypt.checkpw`); username compare uses `secrets.compare_digest`.
- Session `SECRET_KEY` comes from `FLASK_SECRET_KEY` or local `config.json` — not a production secret committed in git.
- Login and logout forms include a **CSRF** token (Flask-WTF).
- Do not commit `.env`, real password hashes you care about, or SSH keys.
- `FLASK_DEBUG` defaults to off; enable only for local development.
