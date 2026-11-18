# PRD: Demo Monitoring Infrastructure (Linux Servers)

## 1. Overview

Local demo web app for internal L1/L2/L3 and application teams to view **real-time** Linux server metrics without SSH login for inspection.

**Problem:** Operators must log into servers to check memory, CPU, network, and port usage.

**Goal:** Read-mostly UI (metrics are read-only) with server inventory management, manual refresh, and basic CPU/memory threshold alerts.

**Scope:** Demo only. Deploy and run on the local machine where Cursor is running. Keep implementation and setup minimal.

---

## 2. Users

| User | Access |
|------|--------|
| Internal L1 / L2 / L3 | Sign in as `admin`, view dashboard and metrics |
| Infrastructure & app teams | Same single shared admin account |

No multi-user roles in this demo.

---

## 3. Goals & Non-Goals

### Goals
- Attractive, simple Flask UI for live Linux metrics
- Sign-in with default user `admin` and bcrypt-hashed password from config
- Add / edit / delete Linux servers to monitor (via SSH)
- Manual refresh of live metrics (no auto-polling, no history)
- Basic CPU and memory threshold alerts on the dashboard

### Non-Goals (out of scope)
- Historical metrics, charts over time, or long-term storage of samples
- Auto-refresh / background polling
- Windows hosts, containers, Kubernetes
- Email / Slack / ticket integrations
- Multi-user accounts, RBAC, SSO
- Production hardening, HA, or remote deployment beyond localhost demo

---

## 4. Features

### 4.1 Sign-in
- Default username: `admin`
- Password stored as **bcrypt hash in a config file**
- Session required for all monitoring pages
- Metrics views are **read-only**; only inventory CRUD and login are interactive writes

### 4.2 Server inventory (CRUD)
- Create, read, update, delete Linux server entries
- Fields (minimum): name/label, host (IP or hostname), SSH port, SSH username, auth (password or key path as implemented for demo)
- App connects over **SSH** to collect metrics on demand

### 4.3 Dashboard
- List all configured servers with latest fetched status (after manual refresh)
- Show basic **alert state** when CPU or memory exceeds configured thresholds
- Navigate to a server detail view

### 4.4 Server metrics (real-time, on demand)
On manual refresh, collect and display:

| Metric | Details |
|--------|---------|
| CPU | Current usage % |
| Memory | Used / total (and %) |
| Network | Interface rx/tx throughput **and** connection count |
| Ports | **Listening** ports only (and bound process if easily available over SSH) |

No historical retention of metric samples.

### 4.5 Alerts (basic)
- Configurable CPU % and memory % thresholds (config or simple UI setting)
- Dashboard highlights servers currently over threshold based on last manual fetch
- No external notifications

### 4.6 Manual refresh
- Explicit Refresh action on dashboard and/or detail page
- Each refresh triggers SSH collection for the relevant server(s)

---

## 5. Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python |
| Web | Flask |
| UI | Server-rendered templates + CSS (attractive, simple) |
| Auth | Flask session + bcrypt password hash in config |
| Remote access | SSH to Linux hosts |
| Runtime | Localhost demo |

---

## 6. Local run (minimal)

1. Create/activate a Python virtualenv
2. Install dependencies from `requirements.txt`
3. Set `admin` bcrypt password hash in config file
4. Run Flask app (e.g. `flask run` or `python app.py`)
5. Open UI in browser on localhost
6. Sign in as `admin`, add a Linux server, refresh metrics

Exact commands and file names to be filled during implementation.

---

## 7. Acceptance criteria

- [x] Unauthenticated users cannot see metrics or inventory
- [x] Login works with `admin` + password matching bcrypt hash in config
- [x] Operator can add, edit, and delete Linux server entries
- [x] Manual refresh returns CPU, memory, network (rx/tx + connection count), and listening ports
- [x] Dashboard shows servers and basic CPU/memory threshold alerts
- [x] Metrics UI does not allow mutating remote host state
- [x] App runs locally with minimal setup steps above

---

## 8. Decisions captured

| Topic | Decision |
|-------|----------|
| Data mode | Real-time only |
| Refresh | Manual |
| Network | rx/tx + connection count |
| Ports | Listening only |
| Collection | SSH |
| Deploy | Local demo |
| Auth | Single `admin`, bcrypt in config |
| Inventory | Full CRUD |
| Alerts | Basic CPU/memory % on dashboard |
| UI | Dashboard + server detail |
| Depth | Basic demo only |
