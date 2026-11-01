"""Controlled public fetch + real agent-browser DOM read in a networkless namespace.

Each redirect is DNS/IP checked and pinned before fetching. Browser sees only that
captured HTML through its own loopback. Dynamic external resources are unavailable.
"""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import multiprocessing
import os
import signal
import socket
import ssl
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit


def validate_url(url: str, domains: list[str]) -> tuple[str, int]:
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    if (
        p.scheme != "https"
        or p.port not in (None, 443)
        or p.username
        or p.password
        or host not in domains
        or p.fragment
    ):
        raise ValueError("Only exact allowlisted public HTTPS hosts on port 443 are granted")
    return host, 443


def fetch_public(url, domains, deadline=None):
    for _ in range(4):
        timeout = min(12, max(0.001, deadline - time.monotonic())) if deadline else 12
        host, port = validate_url(url, domains)
        addresses = {x[4][0] for x in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(x).is_global for x in addresses):
            raise ValueError("Non-public DNS destination refused")
        conn = http.client.HTTPSConnection(host, port, timeout=timeout)
        # Pin the validated address while retaining certificate verification + original SNI.
        raw = socket.create_connection((sorted(addresses)[0], port), timeout=timeout)
        try:
            conn.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
            p = urlsplit(url)
            path = (p.path or "/") + (("?" + p.query) if p.query else "")
            conn.request(
                "GET",
                path,
                headers={"User-Agent": "KeplerResearch/1.0 (read-only)", "Accept": "text/html"},
            )
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                url = urljoin(url, response.getheader("Location", ""))
                continue
            if response.status != 200 or "text/html" not in response.getheader("Content-Type", ""):
                raise ValueError("Public page unavailable or not HTML")
            body = response.read(1000001)
            if len(body) > 1000000:
                raise ValueError("Browser document exceeds 1 MB")
            return body, url
        finally:
            conn.close()
            raw.close()
    raise ValueError("Redirect limit exceeded")


def checked_hash(path, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Pinned executable hash mismatch: " + path.name)


def _fetch_child(pipe, url, domains, deadline):
    try:
        pipe.send((True, fetch_public(url, domains, deadline)))
    except Exception as exc:
        pipe.send((False, (type(exc).__name__, str(exc))))
    finally:
        pipe.close()


def _check_job(deadline, cancelled):
    if cancelled is not None and cancelled.is_set():
        raise TimeoutError("Research cancelled during browser job")
    if time.monotonic() >= deadline:
        raise TimeoutError("Browser job exceeded 100 seconds")


def _supervised_fetch(url, domains, deadline, cancelled):
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_fetch_child, args=(send, url, domains, deadline))
    process.start()
    send.close()
    try:
        while True:
            _check_job(deadline, cancelled)
            if receive.poll(min(0.1, max(0, deadline - time.monotonic()))):
                ok, result = receive.recv()
                if not ok:
                    raise ValueError("Public fetch failed: " + result[0] + ": " + result[1])
                return result
            if not process.is_alive():
                raise RuntimeError("Public fetch process exited without a result")
    finally:
        receive.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join()


def read_public_page(settings, url, cancelled=None, *, with_metadata=False):
    deadline = time.monotonic() + 100
    _check_job(deadline, cancelled)
    checked_hash(settings.browser_binary, settings.browser_sha256)
    body, source = _supervised_fetch(url, settings.browser_domains, deadline, cancelled)
    _check_job(deadline, cancelled)
    settings.state_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix="browser-", dir=settings.state_root) as tmp:
        work = Path(tmp)
        (work / "page.html").write_bytes(body)
        # Copy the verified executable, not a personal browser profile or cookies.
        (work / "agent-browser").write_bytes(settings.browser_binary.read_bytes())
        (work / "agent-browser").chmod(0o700)
        cmd = [
            "bwrap",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/bin",
            "/bin",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            "--ro-bind",
            "/opt",
            "/opt",
            "--ro-bind",
            "/etc",
            "/etc",
            "--unshare-user",
            "--uid",
            "0",
            "--gid",
            "0",
            "--unshare-net",
            "--unshare-pid",
            "--unshare-ipc",
            "--die-with-parent",
            "--new-session",
            "--cap-add",
            "CAP_NET_ADMIN",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/home",
            "--tmpfs",
            "/root",
            "--tmpfs",
            "/run",
            "--bind",
            str(work),
            "/work",
            "--ro-bind",
            str(Path(__file__)),
            "/browser.py",
            "--chdir",
            "/work",
            "/usr/bin/python3",
            "/browser.py",
            "--inner",
            str(settings.chrome_binary),
        ]
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            start_new_session=True,
        )
        try:
            while True:
                _check_job(deadline, cancelled)
                try:
                    stdout, stderr = p.communicate(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    continue
        except BaseException:
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            raise
        if p.returncode:
            raise RuntimeError("Isolated agent-browser failed: " + stderr.decode()[-300:])
        result = json.loads(stdout.decode().splitlines()[-1])
        body = result["body"]
        if with_metadata:
            return (
                body[:12000],
                source,
                {
                    "scope": "isolated DOM body text; external resources unavailable",
                    "offset_basis": "DOM body characters",
                    "offset": 0,
                    "end_offset": min(len(body), 12000),
                    "truncated": len(body) > 12000,
                    "completeness": "unknown; public HTML only",
                },
            )
        return body[:12000], source


def inner(chrome):
    import fcntl
    import http.server
    import struct
    import threading

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
        fcntl.ioctl(control.fileno(), 0x8914, struct.pack("16sh", b"lo", 1))

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            if self.path != "/":
                self.send_error(404)
                return
            data = Path("/work/page.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 19090), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    cli = [
        "/work/agent-browser",
        "--session",
        "research",
        "--allowed-domains",
        "127.0.0.1",
        "--executable-path",
        chrome,
    ]
    env = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "XDG_CACHE_HOME": "/tmp/cache"}
    try:
        outputs = []
        for args in [["open", "http://127.0.0.1:19090/"], ["snapshot"], ["get", "text", "body"]]:
            p = subprocess.run(cli + args, env=env, capture_output=True, text=True, timeout=25)
            if p.returncode:
                raise RuntimeError(p.stderr[-300:])
            outputs.append(p.stdout)
        print(json.dumps({"body": outputs[-1], "snapshot": outputs[-2][:2000]}))
    finally:
        subprocess.run(cli + ["close"], env=env, capture_output=True, timeout=15)
        server.shutdown()


if __name__ == "__main__":
    import sys

    inner(sys.argv[2])
