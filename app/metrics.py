"""Parse untrusted remote /proc outputs into UI-safe metric structures."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.ssh_client import SSHError, SSHTarget, run_many


def _clamp_pct(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def parse_cpu_percent(raw: str) -> float | None:
    """Parse two `cpu ` lines from /proc/stat (before/after sleep)."""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip().startswith("cpu ")]
    if len(lines) < 2:
        return None

    def parts(line: str) -> list[int]:
        bits = line.split()[1:]
        return [int(x) for x in bits]

    try:
        a, b = parts(lines[0]), parts(lines[1])
    except (ValueError, IndexError):
        return None
    if len(a) < 4 or len(b) < 4:
        return None
    idle_a, idle_b = a[3], b[3]
    total_a, total_b = sum(a), sum(b)
    d_total = total_b - total_a
    d_idle = idle_b - idle_a
    if d_total <= 0:
        return None
    return _clamp_pct(100.0 * (1.0 - (d_idle / d_total)))


def parse_memory(raw: str) -> dict[str, Any] | None:
    vals: dict[str, int] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        num = rest.strip().split()[0]
        try:
            vals[key] = int(num)
        except ValueError:
            continue
    total = vals.get("MemTotal")
    available = vals.get("MemAvailable")
    if total is None or total <= 0:
        return None
    if available is None:
        free = vals.get("MemFree", 0)
        buffers = vals.get("Buffers", 0)
        cached = vals.get("Cached", 0)
        available = free + buffers + cached
    used = max(0, total - available)
    pct = _clamp_pct(100.0 * used / total)
    # /proc/meminfo is kB
    return {
        "total_kb": total,
        "used_kb": used,
        "available_kb": available,
        "percent": pct,
    }


def parse_network(netdev_raw: str, tcp_raw: str, tcp6_raw: str) -> dict[str, Any]:
    interfaces: list[dict[str, Any]] = []
    for line in netdev_raw.splitlines():
        if ":" not in line or line.strip().startswith("Inter") or line.strip().startswith("face"):
            continue
        name, rest = line.split(":", 1)
        name = name.strip()
        cols = rest.split()
        if len(cols) < 9:
            continue
        try:
            rx = int(cols[0])
            tx = int(cols[8])
        except ValueError:
            continue
        if name == "lo":
            continue
        interfaces.append({"name": name[:32], "rx_bytes": rx, "tx_bytes": tx})

    def conn_lines(blob: str) -> int:
        # Skip header line when present
        lines = [ln for ln in blob.splitlines() if ln.strip()]
        if lines and lines[0].strip().lower().startswith("sl"):
            lines = lines[1:]
        return len(lines)

    connections = conn_lines(tcp_raw) + conn_lines(tcp6_raw)
    return {"interfaces": interfaces, "connection_count": connections}


def parse_listening_ports(tcp_raw: str, tcp6_raw: str) -> list[dict[str, Any]]:
    """Parse LISTEN (state 0A) entries from /proc/net/tcp{,6}."""

    def parse_blob(blob: str, ipv6: bool = False) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in blob.splitlines():
            parts = line.split()
            if len(parts) < 10 or parts[0] == "sl":
                continue
            local = parts[1]
            state = parts[3].upper()
            if state != "0A":
                continue
            try:
                addr_hex, port_hex = local.split(":")
                port = int(port_hex, 16)
            except ValueError:
                continue
            rows.append(
                {
                    "port": port,
                    "protocol": "tcp6" if ipv6 else "tcp",
                    "state": "LISTEN",
                }
            )
        return rows

    combined = parse_blob(tcp_raw, False) + parse_blob(tcp6_raw, True)
    # Dedupe by protocol+port
    seen: set[tuple[str, int]] = set()
    out: list[dict[str, Any]] = []
    for row in sorted(combined, key=lambda r: (r["protocol"], r["port"])):
        key = (row["protocol"], row["port"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def collect_metrics(target: SSHTarget, run_fn=run_many) -> dict[str, Any]:
    """Fetch and parse all demo metrics over SSH (read-only)."""
    raw = run_fn(
        target,
        ["cpu_sample", "meminfo", "netdev", "tcp", "tcp6"],
    )
    cpu = parse_cpu_percent(raw.get("cpu_sample", ""))
    mem = parse_memory(raw.get("meminfo", ""))
    net = parse_network(raw.get("netdev", ""), raw.get("tcp", ""), raw.get("tcp6", ""))
    ports = parse_listening_ports(raw.get("tcp", ""), raw.get("tcp6", ""))
    if cpu is None and mem is None:
        raise SSHError("Could not parse CPU/memory from remote host")
    return {
        "cpu_percent": cpu,
        "memory": mem,
        "network": net,
        "listening_ports": ports,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
