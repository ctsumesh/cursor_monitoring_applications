"""SSH helper: run allowlisted read-only remote commands only."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import paramiko

logger = logging.getLogger(__name__)

# Fixed remote commands — never accept free-form shell from the UI.
ALLOWED_COMMANDS: dict[str, str] = {
    "cpu_sample": "head -n 1 /proc/stat; sleep 0.4; head -n 1 /proc/stat",
    "meminfo": "cat /proc/meminfo",
    "netdev": "cat /proc/net/dev",
    "tcp": "cat /proc/net/tcp",
    "tcp6": "cat /proc/net/tcp6 2>/dev/null || true",
}


@dataclass
class SSHTarget:
    host: str
    port: int
    username: str
    auth_type: str  # password | key
    password: str = ""
    key_path: str = ""


class SSHError(RuntimeError):
    """User-facing SSH failure (message must not include secrets)."""


def _connect(target: SSHTarget, timeout: float = 8.0) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    # Demo: accept unknown hosts so local/lab IPs work; document in README.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict = {
        "hostname": target.host,
        "port": int(target.port),
        "username": target.username,
        "timeout": timeout,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if target.auth_type == "key":
        key_file = Path(target.key_path).expanduser()
        if not key_file.is_file():
            raise SSHError("SSH key file not found")
        connect_kwargs["key_filename"] = str(key_file)
    else:
        connect_kwargs["password"] = target.password or ""
    try:
        client.connect(**connect_kwargs)
    except paramiko.AuthenticationException as exc:
        raise SSHError("SSH authentication failed") from exc
    except paramiko.SSHException as exc:
        raise SSHError(f"SSH error: {exc.__class__.__name__}") from exc
    except OSError as exc:
        raise SSHError(f"SSH connection failed: {exc.__class__.__name__}") from exc
    logger.info(
        "SSH connected host=%s port=%s user=%s auth=%s",
        target.host,
        target.port,
        target.username,
        target.auth_type,
    )
    return client


def run_allowlisted(
    target: SSHTarget,
    command_key: str,
    *,
    timeout: float = 8.0,
    connect_fn: Callable[[SSHTarget, float], paramiko.SSHClient] | None = None,
) -> str:
    """
    Run a single allowlisted command key. Raises SSHError / KeyError.
    """
    if command_key not in ALLOWED_COMMANDS:
        raise KeyError(f"Command not allowlisted: {command_key}")
    remote = ALLOWED_COMMANDS[command_key]
    opener = connect_fn or _connect
    client = None
    try:
        client = opener(target, timeout)
        _stdin, stdout, stderr = client.exec_command(remote, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if exit_status != 0 and not out:
            raise SSHError(f"Remote command failed ({command_key})")
        if err and exit_status != 0:
            # Do not surface raw stderr paths that might leak env; keep generic + key
            raise SSHError(f"Remote command failed ({command_key})")
        return out
    except SSHError:
        raise
    except paramiko.AuthenticationException as exc:
        raise SSHError("SSH authentication failed") from exc
    except Exception as exc:  # noqa: BLE001 — map to safe UI message
        if "timed out" in str(exc).lower() or exc.__class__.__name__ == "timeout":
            raise SSHError("SSH command timed out") from exc
        raise SSHError(f"SSH command error: {exc.__class__.__name__}") from exc
    finally:
        if client is not None:
            client.close()


def run_many(
    target: SSHTarget,
    command_keys: list[str],
    *,
    timeout: float = 8.0,
    connect_fn: Callable[[SSHTarget, float], paramiko.SSHClient] | None = None,
) -> dict[str, str]:
    """Open one SSH session and run several allowlisted commands."""
    for key in command_keys:
        if key not in ALLOWED_COMMANDS:
            raise KeyError(f"Command not allowlisted: {key}")
    opener = connect_fn or _connect
    client = None
    results: dict[str, str] = {}
    try:
        client = opener(target, timeout)
        for key in command_keys:
            remote = ALLOWED_COMMANDS[key]
            _stdin, stdout, stderr = client.exec_command(remote, timeout=timeout)
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="replace")
            if exit_status != 0 and not out.strip():
                raise SSHError(f"Remote command failed ({key})")
            results[key] = out
        return results
    except SSHError:
        raise
    except paramiko.AuthenticationException as exc:
        raise SSHError("SSH authentication failed") from exc
    except Exception as exc:  # noqa: BLE001
        if "timed out" in str(exc).lower():
            raise SSHError("SSH command timed out") from exc
        raise SSHError(f"SSH command error: {exc.__class__.__name__}") from exc
    finally:
        if client is not None:
            client.close()
