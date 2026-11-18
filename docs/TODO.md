# TODO: Demo Monitoring Infrastructure

Small, AI-friendly increments. Complete in order. Each step includes **security** and **docs**.

Demo scope: run locally where Cursor is running. Prefer minimal files and steps.

---

## Step 1 — Project initialization + basic UI

- [x] Create Flask app skeleton (`app.py` or `app/` package), `requirements.txt`, `.gitignore`
- [x] Add a minimal attractive base layout (HTML template + CSS): header, nav placeholder, content area
- [x] Add a public home/landing page that loads without auth
- [x] **Security:** do not commit secrets; add `.env` / config examples to `.gitignore`; use a non-debug default for anything shared later
- [x] **Docs:** short `README.md` with venv create, `pip install -r requirements.txt`, and how to run on localhost

---

## Step 2 — Sign-in + unit tests

- [x] Add config file support for `admin` username + **bcrypt** password hash (no plaintext password in repo)
- [x] Implement login form + Flask session sign-in / sign-out
- [x] Protect placeholder dashboard route (redirect if not logged in)
- [x] Add unit tests for password verify, login success/failure, and protected-route redirect
- [x] **Security:** bcrypt only; constant-time compare via library; secure session `SECRET_KEY` from env/config (not hardcoded in git); CSRF token on login form
- [x] **Docs:** document how to generate a bcrypt hash and set it in config; document test command (`pytest`)

---

## Step 3 — CI/CD (GitHub Actions)

- [x] Add `.github/workflows/ci.yml`: install deps, run linters (optional/light), run unit tests on push/PR
- [x] Pin or range Python version in CI to match local demo
- [x] **Security:** no secrets in workflow logs; use CI-only dummy config/hash for tests; do not publish artifacts containing credentials
- [x] **Docs:** note in `README.md` that CI runs tests on GitHub Actions; link to workflow file

---

## Step 4 — Server inventory model (CRUD backend)

- [ ] Define server fields: name, host, SSH port, SSH username, auth material reference (password or key path for demo)
- [ ] Persist inventory locally (simple JSON/SQLite—pick one and keep it small)
- [ ] Implement add / list / update / delete functions (no UI polish yet if needed; routes OK)
- [ ] Unit tests for CRUD validation (reject empty host, invalid port, etc.)
- [ ] **Security:** never log SSH passwords/keys; store secrets outside git when possible; validate/sanitize host and port input
- [ ] **Docs:** document inventory storage location and field meanings

---

## Step 5 — Server inventory UI

- [ ] Pages/forms: list servers, add server, edit server, delete with confirm
- [ ] Require login for all inventory routes
- [ ] **Security:** CSRF on mutating forms; authorize all actions behind session; escape all user-provided fields in templates (XSS)
- [ ] **Docs:** screenshot or short “how to add a server” section in `README.md`

---

## Step 6 — SSH connection helper (read-only commands)

- [ ] Add SSH client helper to run allowlisted read-only remote commands
- [ ] Connection timeout + clear error messages for UI
- [ ] Unit tests with mocked SSH (success, auth failure, timeout)
- [ ] **Security:** allowlist commands only (no free-form shell from UI); disable unknown host destructive flows for demo or document known_hosts approach; never expose private key contents in UI/logs
- [ ] **Docs:** document required SSH access and demo limitation (local/lab hosts only)

---

## Step 7 — Collect CPU + memory (manual refresh)

- [ ] On Refresh, fetch CPU % and memory used/total/% over SSH
- [ ] Show results on server detail page (read-only)
- [ ] Tests with mocked command output parsers
- [ ] **Security:** parse output safely; treat remote output as untrusted data in UI
- [ ] **Docs:** note which remote commands/files are used for CPU/memory

---

## Step 8 — Collect network metrics

- [ ] On Refresh, collect interface rx/tx throughput and connection count
- [ ] Display on server detail page
- [ ] Parser unit tests
- [ ] **Security:** allowlisted commands only; sanitize display values
- [ ] **Docs:** document network metric sources

---

## Step 9 — Collect listening ports

- [ ] On Refresh, collect listening ports (and bound process if simple over SSH)
- [ ] Display on server detail page
- [ ] Parser unit tests
- [ ] **Security:** read-only; no port bind/kill actions in UI
- [ ] **Docs:** document how listening ports are gathered

---

## Step 10 — Dashboard + manual refresh all

- [ ] Dashboard lists all servers with last-fetched CPU/memory summary (or “not yet refreshed”)
- [ ] Manual “Refresh” per server and/or refresh visible set
- [ ] Link dashboard rows to server detail
- [ ] **Security:** all dashboard routes behind login; no remote mutation
- [ ] **Docs:** update `README.md` with main user flow (login → add server → refresh → view)

---

## Step 11 — Basic CPU/memory alerts

- [ ] Config thresholds for CPU % and memory %
- [ ] Highlight servers over threshold on dashboard after last refresh
- [ ] Unit tests for threshold evaluation
- [ ] **Security:** thresholds are local config only; no external notification side effects
- [ ] **Docs:** document default thresholds and how to change them

---

## Step 12 — Hardening pass + final demo docs

- [ ] Confirm metrics UI is read-only; inventory CRUD + login are the only writes
- [ ] Review `.gitignore`, sample config, and that real hashes/keys are not committed
- [ ] Smoke-test full local flow on the Cursor machine
- [ ] **Security:** checklist—session secret, bcrypt, CSRF, SSH allowlist, no secret logging, XSS escaping
- [ ] **Docs:** finalize minimal `README.md` runbook; keep `docs/requirements.md` and this `docs/TODO.md` in sync with what shipped

---

## Progress tracking

| Step | Focus | Status |
|------|--------|--------|
| 1 | Init + basic UI | Done |
| 2 | Sign-in + unit tests | Done |
| 3 | GitHub Actions CI | Done |
| 4 | Inventory backend | Pending |
| 5 | Inventory UI | Pending |
| 6 | SSH helper | Pending |
| 7 | CPU + memory | Pending |
| 8 | Network metrics | Pending |
| 9 | Listening ports | Pending |
| 10 | Dashboard + refresh | Pending |
| 11 | Alerts | Pending |
| 12 | Hardening + docs | Pending |
