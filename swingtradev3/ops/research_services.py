"""Manage the personal host research services; leave broker services independent.

Credentials are read from the running Kepler API/container and written only to
private systemd environment files, never command arguments or console output.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

import httpx
from sqlalchemy.engine import make_url

from research_room.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
STATE = Path.home() / ".local/state/kepler-rooms"
UNITS = {
    "models": "kepler-research-models.service",
    "api": "kepler-research-api.service",
    "worker": "kepler-research-worker.scope",
}


def inspect(name):
    return json.loads(subprocess.check_output(["docker", "inspect", name], text=True))[0]


def private_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, text.encode())
    finally:
        os.close(fd)


def write_environment(path, values):
    private_write(
        path, "".join(f"{key}={json.dumps(str(value))}\n" for key, value in values.items())
    )


def prepare():
    config_path = STATE / "local.json"
    if not config_path.exists():
        settings = json.loads((ROOT / "swingtradev3/research_room/local.example.json").read_text())
        settings["state_root"] = str(STATE / "runtime")
        settings["browser_domains"] = [
            "nseindia.com",
            "www.nseindia.com",
            "sebi.gov.in",
            "www.sebi.gov.in",
            "rbi.org.in",
            "www.rbi.org.in",
        ]
        private_write(config_path, json.dumps(settings, indent=2) + "\n")
    config = Settings.model_validate(json.loads(config_path.read_text()))
    if config.state_root.name.startswith("validation-") or "/validation-" in str(config.state_root):
        raise RuntimeError("Use an application runtime directory separate from old validation runs")
    config.state_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    app = inspect("swingtradev3-app")
    app_env = dict(x.split("=", 1) for x in app["Config"]["Env"] if "=" in x)
    db = inspect("swingtradev3-db")
    ports = db["NetworkSettings"]["Ports"].get("5432/tcp") or []
    if not ports:
        raise RuntimeError("Kepler Postgres needs a host-reachable published port")
    database = make_url(app_env["DATABASE_URL"]).set(
        host="127.0.0.1", port=int(ports[0]["HostPort"])
    )
    key = app_env.get("FASTAPI_API_KEY") or app_env.get("API_KEY", "")
    if not key:
        raise RuntimeError("The normal Kepler API must have its existing API key configured")
    graph = inspect("swingtradev3-memgraph")
    graph_ports = graph["NetworkSettings"]["Ports"].get("7687/tcp") or []
    if not graph_ports:
        raise RuntimeError("Kepler graph needs a host-reachable published port")
    common = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "KEPLER_RESEARCH_CONFIG": str(config_path),
        "PYTHONUNBUFFERED": "1",
    }
    database_env = {
        "DATABASE_URL": database.render_as_string(hide_password=False),
        "MEMGRAPH_URI": "bolt://127.0.0.1:" + graph_ports[0]["HostPort"],
        "MEMGRAPH_DATABASE": app_env.get("MEMGRAPH_DATABASE", "memgraph"),
        "MEMGRAPH_USER": app_env.get("MEMGRAPH_USER", ""),
        "MEMGRAPH_PASSWORD": app_env.get("MEMGRAPH_PASSWORD", ""),
    }
    write_environment(STATE / "models.env", common)
    write_environment(STATE / "worker.env", {**common, **database_env})
    write_environment(STATE / "api.env", {**common, **database_env, "FASTAPI_API_KEY": key})
    return config


def active(name):
    return (
        subprocess.run(["systemctl", "--user", "is-active", "--quiet", UNITS[name]]).returncode == 0
    )


def launch(name, args):
    if active(name):
        print(name, "already running", flush=True)
        return
    if name == "worker":
        # A scope inherits this user's IDE/terminal security context. A service is
        # spawned by the user manager, whose Ubuntu AppArmor context can deny the
        # same unprivileged sandbox. Keep bwrap isolation; do not change policy.
        probe = subprocess.run(
            [
                "bwrap",
                "--unshare-user",
                "--ro-bind",
                "/usr",
                "/usr",
                "--ro-bind",
                "/lib",
                "/lib",
                "--ro-bind",
                "/lib64",
                "/lib64",
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "/usr/bin/true",
            ],
            capture_output=True,
            timeout=5,
        )
        if probe.returncode:
            raise RuntimeError(
                "This terminal cannot create the required sandbox. Start from the working IDE terminal; no host security setting was changed"
            )
        environment = {
            key: json.loads(value)
            for line in (STATE / "worker.env").read_text().splitlines()
            for key, value in [line.split("=", 1)]
        }
        environment.update(
            {
                key: os.environ[key]
                for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS")
                if key in os.environ
            }
        )
        log = (STATE / "worker.log").open("a")
        process = subprocess.Popen(
            [
                "systemd-run",
                "--user",
                "--scope",
                "--quiet",
                "--collect",
                "--unit",
                UNITS[name],
                str(Path(sys.executable).absolute()),
                *args,
            ],
            cwd=ROOT / "swingtradev3",
            env=environment,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        log.close()
        for _ in range(50):
            if active(name):
                print(name, "running in managed scope", flush=True)
                return
            if process.poll() is not None:
                raise RuntimeError("Research worker scope failed; inspect the private worker log")
            time.sleep(0.1)
        raise RuntimeError("Research worker scope did not become active")
    # Clear only this tool's stopped transient unit; never stop an unrelated service.
    subprocess.run(["systemctl", "--user", "reset-failed", UNITS[name]], capture_output=True)
    cmd = [
        "systemd-run",
        "--user",
        "--quiet",
        "--collect",
        "--unit",
        UNITS[name],
        "--property",
        "WorkingDirectory=" + str(ROOT / "swingtradev3"),
        "--property",
        "EnvironmentFile=" + str(STATE / (name + ".env")),
        "--property",
        "Restart=on-failure",
        "--property",
        "RestartSec=10",
        "--property",
        "StartLimitIntervalSec=300",
        "--property",
        "StartLimitBurst=3",
        "--property",
        "TimeoutStopSec=25",
        "--property",
        "KillMode=control-group",
        str(Path(sys.executable).absolute()),
        *args,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(name, "starting", flush=True)


def wait_for_models(config):
    opener = build_opener(ProxyHandler({}))
    end = time.monotonic() + 300
    while time.monotonic() < end:
        ready = []
        for profile in config.profiles.values():
            try:
                with opener.open(profile.endpoint + "/models", timeout=1) as response:
                    ready.append(profile.model in [x["id"] for x in json.load(response)["data"]])
            except (OSError, ValueError):
                ready.append(False)
        if all(ready):
            print("Both pinned local models ready", flush=True)
            return
        if not active("models"):
            raise RuntimeError(
                "Model service stopped; inspect journalctl --user -u " + UNITS["models"]
            )
        time.sleep(0.5)
    raise TimeoutError("Models did not become ready within the 300-second startup ceiling")


def start():
    config = prepare()
    socket_path = ROOT / "swingtradev3/logs/research-api.sock"
    if socket_path.exists() and not active("api"):
        # Refuse a listener owned by another process. Remove only a stale Unix socket.
        with socket.socket(socket.AF_UNIX) as check:
            if check.connect_ex(str(socket_path)) == 0:
                raise RuntimeError("Research API socket already has a different owner")
        if not socket_path.is_socket():
            raise RuntimeError("Refusing to replace a non-socket research path")
        socket_path.unlink()
    launch("api", ["-m", "research_room.host_api", str(socket_path)])
    for _ in range(100):
        try:
            with httpx.Client(
                transport=httpx.HTTPTransport(uds=str(socket_path)), timeout=1
            ) as client:
                if client.get("http://research/research/rooms").status_code == 403:
                    socket_path.chmod(0o600)
                    break
        except httpx.TransportError:
            pass
        time.sleep(0.1)
    else:
        raise RuntimeError("Host research API did not start or did not enforce authentication")
    launch("models", ["-m", "research_room.models"])
    wait_for_models(config)
    launch("worker", ["-m", "research_room.worker"])
    print("Research services started; normal dashboard: http://localhost:8502", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"])
    args = parser.parse_args()
    if args.action == "start":
        start()
    elif args.action == "stop":
        for name in ("worker", "models", "api"):
            subprocess.run(["systemctl", "--user", "stop", UNITS[name]], check=False)
    else:
        for name in UNITS:
            print(name + ": " + ("running" if active(name) else "stopped"))


if __name__ == "__main__":
    main()
