"""Opt-in measured pair supervisor; only signals its own children.

Exact F flags intentionally retain default CPU embeddings. No downloads, driver
changes, or termination of existing model/application services.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler

from .browser import checked_hash
from .settings import load_settings


def resource_guard(settings):
    available = next(
        int(x.split()[1]) / 1024
        for x in Path("/proc/meminfo").read_text().splitlines()
        if x.startswith("MemAvailable:")
    )
    if available < 1536:
        raise RuntimeError("System available RAM below 1536 MiB floor")
    raw = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=uuid,memory.free", "--format=csv,noheader,nounits"],
        text=True,
        timeout=5,
    )
    free = {
        parts[0].strip(): int(parts[1]) for row in raw.splitlines() if (parts := row.split(","))
    }
    if any(free.get(p.gpu_uuid, 0) < 1024 for p in settings.profiles.values()):
        raise RuntimeError("Assigned GPU unavailable or below 1024 MiB free floor")


def main():
    settings = load_settings()
    checked_hash(settings.llama_binary, settings.llama_sha256)
    settings.state_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    stop, owned = threading.Event(), []
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    opener = build_opener(ProxyHandler({}))
    try:
        for role, profile in settings.profiles.items():
            port = urlsplit(profile.endpoint).port
            with socket.socket() as check:
                if check.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(f"Port {port} already owned; refusing to replace a service")
            resource_guard(settings)
            checked_hash(profile.model_path, profile.gguf_sha256)
            args = [
                str(settings.llama_binary),
                "-m",
                str(profile.model_path),
                "--alias",
                profile.model,
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--ctx-size",
                "32768",
                "--parallel",
                "1",
                "--n-gpu-layers",
                "99",
                "--split-mode",
                "none",
                "--main-gpu",
                "0",
                "--flash-attn",
                "on",
                "--cache-type-k",
                "f16",
                "--cache-type-v",
                "f16",
                "--batch-size",
                "256",
                "--ubatch-size",
                "128",
                "--threads",
                "2",
                "--threads-batch",
                "2",
                "--cache-ram",
                "0",
                "--metrics",
                "--jinja",
                "--reasoning-budget",
                "0",
            ]
            log = (settings.state_root / f"{role}-model.log").open("w")
            process = subprocess.Popen(
                args,
                env={
                    "PATH": "/usr/bin:/bin",
                    "LANG": "C.UTF-8",
                    "CUDA_VISIBLE_DEVICES": profile.gpu_uuid,
                    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
                    "OMP_NUM_THREADS": "2",
                },
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
            owned.append((process, log))
            start = time.monotonic()
            while time.monotonic() - start < 300 and not stop.is_set():
                if process.poll() is not None:
                    raise RuntimeError(f"{role} model process exited; inspect its local log")
                resource_guard(settings)
                try:
                    with opener.open(f"http://127.0.0.1:{port}/v1/models", timeout=1) as response:
                        identity = json.load(response)
                    if profile.model not in [x["id"] for x in identity["data"]]:
                        raise RuntimeError("Wrong model identity at local endpoint")
                    print(role, "READY", profile.model, flush=True)
                    break
                except (OSError, TimeoutError):
                    stop.wait(0.5)
            else:
                raise RuntimeError("Model startup interrupted or timed out")
        while not stop.wait(1):
            resource_guard(settings)
            if any(p.poll() is not None for p, _ in owned):
                raise RuntimeError("Owned model service exited")
    finally:
        for process, log in reversed(owned):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
            log.close()


if __name__ == "__main__":
    main()
