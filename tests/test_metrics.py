"""Parser unit tests for CPU, memory, network, and listening ports."""

from app.metrics import (
    collect_metrics,
    parse_cpu_percent,
    parse_listening_ports,
    parse_memory,
    parse_network,
)
from app.ssh_client import SSHTarget


def test_parse_cpu_percent():
    raw = (
        "cpu  100 0 0 100 0 0 0 0 0 0\n"
        "cpu  120 0 0 110 0 0 0 0 0 0\n"
    )
    # total delta 30, idle delta 10 => 66.7% busy
    assert parse_cpu_percent(raw) == 66.7


def test_parse_memory():
    raw = """MemTotal:       1000 kB
MemFree:         100 kB
MemAvailable:    400 kB
Buffers:          50 kB
Cached:          100 kB
"""
    mem = parse_memory(raw)
    assert mem["total_kb"] == 1000
    assert mem["used_kb"] == 600
    assert mem["percent"] == 60.0


def test_parse_network_and_ports():
    netdev = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
  eth0: 1000 1 0 0 0 0 0 0 2000 1 0 0 0 0 0 0
    lo: 10 1 0 0 0 0 0 0 10 1 0 0 0 0 0 0
"""
    # local_address with port 0050 (80) state 0A LISTEN
    tcp = """  sl  local_address rem_address   st
   0: 00000000:0050 00000000:0000 0A 00000000:00000000 00:00000000 00000000  0        0 0 1
   1: 0100007F:01BB 00000000:0000 01 00000000:00000000 00:00000000 00000000  0        0 0 1
"""
    net = parse_network(netdev, tcp, "")
    assert net["connection_count"] == 2
    assert net["interfaces"][0]["name"] == "eth0"
    assert net["interfaces"][0]["rx_bytes"] == 1000
    assert net["interfaces"][0]["tx_bytes"] == 2000
    ports = parse_listening_ports(tcp, "")
    assert {"port": 80, "protocol": "tcp", "state": "LISTEN"} in ports


def test_collect_metrics_with_stub():
    def fake_run(target, keys, **kwargs):
        return {
            "cpu_sample": "cpu  10 0 0 10 0 0 0\ncpu  20 0 0 15 0 0 0\n",
            "meminfo": "MemTotal: 2000 kB\nMemAvailable: 500 kB\n",
            "netdev": "eth0: 1 0 0 0 0 0 0 0 2 0 0 0 0 0 0 0\n",
            "tcp": (
                "  sl  local_address rem_address   st\n"
                "   0: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000  0        0 0 1\n"
            ),
            "tcp6": "",
        }

    metrics = collect_metrics(
        SSHTarget("localhost", 22, "u", "password", password="x"),
        run_fn=fake_run,
    )
    assert metrics["cpu_percent"] is not None
    assert metrics["memory"]["percent"] == 75.0
    assert metrics["network"]["connection_count"] == 1
    assert metrics["listening_ports"][0]["port"] == 22
