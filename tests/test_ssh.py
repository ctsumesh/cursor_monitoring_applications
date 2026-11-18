"""SSH helper tests with mocked clients."""

from unittest.mock import MagicMock

import pytest

from app.ssh_client import ALLOWED_COMMANDS, SSHError, SSHTarget, run_allowlisted, run_many


def _fake_client(outputs: dict[str, tuple[str, int]]):
    """Map remote command string -> (stdout, exit_status)."""

    class Chan:
        def __init__(self, code):
            self._code = code

        def recv_exit_status(self):
            return self._code

    class Stream:
        def __init__(self, text, code):
            self.channel = Chan(code)
            self._text = text.encode()

        def read(self):
            return self._text

    client = MagicMock()

    def exec_command(cmd, timeout=8.0):
        out, code = outputs.get(cmd, ("", 1))
        return MagicMock(), Stream(out, code), Stream("", 0)

    client.exec_command.side_effect = exec_command
    return client


def test_rejects_non_allowlisted():
    target = SSHTarget("localhost", 22, "u", "password", password="x")
    with pytest.raises(KeyError):
        run_allowlisted(target, "rm_rf", connect_fn=lambda t, to: MagicMock())


def test_run_allowlisted_success():
    cmd = ALLOWED_COMMANDS["meminfo"]
    client = _fake_client({cmd: ("MemTotal: 100 kB\n", 0)})

    def connect(target, timeout):
        return client

    target = SSHTarget("localhost", 22, "u", "password", password="x")
    out = run_allowlisted(target, "meminfo", connect_fn=connect)
    assert "MemTotal" in out
    client.close.assert_called()


def test_auth_failure_message():
    import paramiko

    def connect(target, timeout):
        raise paramiko.AuthenticationException("bad")

    target = SSHTarget("localhost", 22, "u", "password", password="x")
    with pytest.raises(SSHError, match="authentication failed"):
        run_allowlisted(target, "meminfo", connect_fn=connect)


def test_run_many():
    outputs = {ALLOWED_COMMANDS[k]: (f"{k}-out", 0) for k in ("meminfo", "netdev")}
    client = _fake_client(outputs)

    def connect(target, timeout):
        return client

    target = SSHTarget("localhost", 22, "u", "key", key_path="/tmp/id_rsa")
    result = run_many(target, ["meminfo", "netdev"], connect_fn=connect)
    assert result["meminfo"] == "meminfo-out"
    assert result["netdev"] == "netdev-out"
