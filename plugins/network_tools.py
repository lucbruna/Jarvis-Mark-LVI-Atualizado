"""Local network diagnostics for JARVIS.

Answers the questions a web search is bad at: this machine's addresses, whether
a host is reachable, what a name resolves to, the Wi-Fi link, open sockets and
whether a local port is listening. Everything is read-only and time-limited.
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
from urllib.parse import urlparse

from core import outcome

try:
    import psutil
except Exception:
    psutil = None

_OS = os.name
_MAX_OUTPUT = 1800


PLUGIN = {
    "name": "network_tools",
    "description": (
        "Local network diagnostics: this machine's local and public IP, ping a "
        "host, resolve a DNS name, read the Wi-Fi SSID/signal, list active "
        "connections, and check whether TCP ports are open. Use for 'what is "
        "my IP', 'is google reachable', 'ping 8.8.8.8', 'what is my Wi-Fi', "
        "'what is using this port', or 'is port 8000 open'. This is about the "
        "machine's network, not a web search for facts."
    ),
    "brief": (
        "Local/public IP, ping, DNS, Wi-Fi, active connections and port checks. "
        "Read-only network diagnostics, not web search."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "local_ip | public_ip | ping | dns | wifi | connections | ports"
                ),
                "enum": [
                    "local_ip", "public_ip", "ping", "dns",
                    "wifi", "connections", "ports",
                ],
            },
            "host": {
                "type": "STRING",
                "description": (
                    "For ping/dns/ports: hostname or IP. For ports, defaults to "
                    "127.0.0.1."
                ),
            },
            "count": {
                "type": "INTEGER",
                "description": "For ping: number of echo requests, 1-10. Default 4.",
            },
            "ports": {
                "type": "STRING",
                "description": (
                    "For ports: comma-separated ports or ranges, e.g. "
                    "'80,443,8000-8010'. Default '80,443'."
                ),
            },
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _oem_encoding() -> str:
    if _OS == "nt":
        try:
            import ctypes
            return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
        except Exception:
            return "cp850"
    return "utf-8"


def _run(argv: list[str], timeout: float = 10.0):
    kwargs = {
        "capture_output": True,
        "text": True,
        "encoding": _oem_encoding(),
        "errors": "replace",
        "timeout": timeout,
    }
    if _OS == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(argv, **kwargs)


def _show(player, title: str, text: str) -> None:
    if player and hasattr(player, "show_content"):
        try:
            player.show_content(title, text[:_MAX_OUTPUT])
        except Exception:
            pass


def _clean_host(value) -> str:
    host = str(value or "").strip()
    if not host:
        raise ValueError("host is required")
    if host.startswith("-"):
        raise ValueError("invalid host")
    if "://" in host:
        host = urlparse(host).hostname or host
    host = host.strip().strip("[]")
    if host.count(":") == 1 and not host.startswith("["):
        host = host.split(":", 1)[0]
    return host


def _local_ip() -> str:
    rows = []
    if psutil is not None:
        try:
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        rows.append((iface, addr.address, addr.netmask or ""))
        except Exception:
            pass
    if not rows:
        try:
            for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
                if not ip.startswith("127."):
                    rows.append(("hostname", ip, ""))
        except Exception:
            pass
    if not rows:
        return outcome.failed(
            "network_tools", "no IPv4 address was found", requested_action="local_ip"
        )
    table = "\n".join(
        f"{iface}: {ip}" + (f" (mask {mask})" if mask else "")
        for iface, ip, mask in rows
    )
    return outcome.done(
        "network_tools", requested_action="local_ip", count=len(rows)
    ) + "\n" + table


def _public_ip() -> str:
    import urllib.request

    last = None
    for url in (
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
    ):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "JARVIS/1.0"}
            )
            with urllib.request.urlopen(request, timeout=6) as response:
                ip = response.read(200).decode("utf-8", "replace").strip()
            if ip:
                return outcome.done(
                    "network_tools", requested_action="public_ip", ip=ip
                )
        except Exception as e:
            last = e
    return outcome.failed(
        "network_tools",
        f"could not reach a public-IP service: {last}",
        requested_action="public_ip",
    )


def _ping(host: str, count: int) -> str:
    argv = ["ping", "-n" if _OS == "nt" else "-c", str(count), host]
    proc = _run(argv, timeout=count * 2 + 8)
    text = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    received_match = re.search(r"(?:Received|Recebidos)\s*=\s*(\d+)", text, re.I)
    received = int(received_match.group(1)) if received_match else (
        count if proc.returncode == 0 else 0
    )
    times = [
        float(value.replace(",", "."))
        for value in re.findall(
            r"(?:time|tempo)\s*[=<]\s*(\d+(?:[.,]\d+)?)\s*ms", text, re.I
        )
    ]
    average = round(sum(times) / len(times), 2) if times else None

    if proc.returncode != 0 or received == 0:
        return outcome.failed(
            "network_tools", "host did not respond",
            requested_action="ping", host=host, sent=count, received=received,
            output=text[-800:],
        )
    return outcome.done(
        "network_tools", requested_action="ping",
        host=host, sent=count, received=received, avg_ms=average,
    ) + "\n" + text[-800:]


def _dns(host: str) -> str:
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception as e:
        return outcome.failed(
            "network_tools", f"DNS lookup failed: {e}",
            requested_action="dns", host=host,
        )
    addresses = sorted(
        {str(info[4][0]) for info in infos},
        key=lambda address: (":" in address, address),
    )
    text = "\n".join(addresses)
    return outcome.done(
        "network_tools", requested_action="dns",
        host=host, count=len(addresses),
        addresses=", ".join(addresses),
    ) + "\n" + text


def _wifi() -> str:
    if _OS == "nt":
        proc = _run(["netsh", "wlan", "show", "interfaces"], timeout=10)
        text = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        if proc.returncode != 0:
            return outcome.failed(
                "network_tools", "could not read the Wi-Fi interface",
                requested_action="wifi", output=text[-600:],
            )
        fields = {}
        wanted = {
            "ssid", "signal", "sinal", "state", "estado",
            "authentication", "autenticação", "radio type",
            "tipo de rádio", "receive rate", "taxa de recebimento",
        }
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            if key.lower() in wanted:
                fields[key] = value.strip()
        if not fields:
            return outcome.failed(
                "network_tools",
                "no wireless interface is connected",
                requested_action="wifi",
            )
        summary = "; ".join(f"{key}={value}" for key, value in fields.items())
        return outcome.done(
            "network_tools", requested_action="wifi", details=summary,
        ) + "\n" + text[:1200]

    if _OS == "darwin":
        proc = _run(["airport", "-I"], timeout=8)
        text = proc.stdout or ""
        if not text.strip():
            return outcome.failed(
                "network_tools", "no wireless interface is connected",
                requested_action="wifi",
            )
        return outcome.done(
            "network_tools", requested_action="wifi", details=text.strip()[:800]
        ) + "\n" + text[:1200]

    proc = _run(["iwgetid", "-r"], timeout=8)
    ssid = (proc.stdout or "").strip()
    if not ssid:
        return outcome.failed(
            "network_tools", "no wireless interface is connected",
            requested_action="wifi",
        )
    return outcome.done(
        "network_tools", requested_action="wifi", ssid=ssid
    )


def _connections() -> str:
    if psutil is None:
        return outcome.failed(
            "network_tools",
            "psutil is not installed; run: pip install psutil",
            requested_action="connections",
        )
    try:
        connections = psutil.net_connections(kind="inet")
    except Exception as e:
        return outcome.failed(
            "network_tools", f"could not read connections: {e}",
            requested_action="connections",
        )
    rows = []
    for conn in connections:
        if not conn.laddr:
            continue
        local = f"{conn.laddr.ip}:{conn.laddr.port}"
        remote = (
            f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-"
        )
        name = ""
        if conn.pid:
            try:
                name = psutil.Process(conn.pid).name()
            except Exception:
                pass
        rows.append((local, remote, conn.status or "-", conn.pid or 0, name))
    rows = rows[:30]
    if not rows:
        return outcome.done(
            "network_tools", requested_action="connections", count=0
        ) + "\nNo active inet connections were reported."
    lines = [f"{'LOCAL':<24} {'REMOTE':<24} {'STATUS':<12} {'PID':>6}  PROCESS"]
    for local, remote, status, pid, name in rows:
        lines.append(
            f"{local:<24} {remote:<24} {status:<12} {pid:>6}  {name}"
        )
    table = "\n".join(lines)
    return outcome.done(
        "network_tools", requested_action="connections", count=len(rows)
    ) + "\n" + table


def _parse_ports(raw: str) -> list[int]:
    ports = []
    for part in re.split(r"[,\s]+", str(raw or "")):
        if not part:
            continue
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start, end = int(start), int(end)
            except Exception:
                continue
            if end < start:
                start, end = end, start
            end = min(end, start + 20)
            ports.extend(range(start, end + 1))
        else:
            try:
                ports.append(int(part))
            except Exception:
                continue
    return sorted({p for p in ports if 1 <= p <= 65535})[:20]


def _ports(host: str, raw: str) -> str:
    ports = _parse_ports(raw)
    if not ports:
        return outcome.failed(
            "network_tools", "no valid ports were given",
            requested_action="ports", host=host,
        )
    results = []
    for port in ports:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                results.append((port, True))
        except OSError:
            results.append((port, False))
    lines = [
        f"{port}: {'open' if is_open else 'closed'}" for port, is_open in results
    ]
    table = "\n".join(lines)
    open_count = sum(1 for _, is_open in results if is_open)
    return outcome.done(
        "network_tools", requested_action="ports",
        host=host, checked=len(results), open=open_count,
    ) + "\n" + table


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = str(parameters.get("action") or "").strip().lower()

    try:
        if action == "local_ip":
            result = _local_ip()
            if player and hasattr(player, "show_content"):
                try:
                    player.show_content("LOCAL IP", result)
                except Exception:
                    pass
            return result

        if action == "public_ip":
            return _public_ip()

        if action == "ping":
            host = _clean_host(parameters.get("host"))
            try:
                count = int(parameters.get("count") or 4)
            except Exception:
                count = 4
            count = max(1, min(10, count))
            result = _ping(host, count)
            _show(player, f"PING {host}", result)
            return result

        if action == "dns":
            host = _clean_host(parameters.get("host"))
            result = _dns(host)
            _show(player, f"DNS {host}", result)
            return result

        if action == "wifi":
            result = _wifi()
            _show(player, "WI-FI", result)
            return result

        if action == "connections":
            result = _connections()
            if player and hasattr(player, "show_content"):
                try:
                    player.show_content("CONNECTIONS", result)
                except Exception:
                    pass
            return result

        if action == "ports":
            host = _clean_host(parameters.get("host") or "127.0.0.1")
            result = _ports(host, parameters.get("ports") or "80,443")
            _show(player, f"PORTS {host}", result)
            return result

        return outcome.failed(
            "network_tools",
            f"unknown action '{action}'",
            requested_action=action,
        )

    except Exception as e:
        return outcome.failed(
            "network_tools", str(e), requested_action=action
        )
