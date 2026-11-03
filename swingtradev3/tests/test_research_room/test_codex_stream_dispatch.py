"""Opt-in installed Codex + loopback Bridge protocol check; no inference or provider access."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_room.adapter import Bridge
from research_room.codex import RPC
from research_room.tools import TOOLS

pytestmark = pytest.mark.skipif(
    os.environ.get("KEPLER_CODEX_PROTOCOL_TEST") != "1",
    reason="Explicitly opt in to the installed Codex loopback-only protocol test",
)


class FixtureBudget:
    model_roles = {"fixture": "analyst"}
    turns = {"analyst": 1}

    def admit(self, *_args, **_kwargs):
        return True

    def release(self, *_args):
        pass

    def denial_for(self, _role):
        return None


class StubGateway:
    budget = FixtureBudget()

    def __init__(self):
        self.calls = []

    def granted_tools(self, _role):
        return {"news_search"}

    def begin_turn(self, _role):
        pass

    def execute(self, _role, params):
        self.calls.append(params)
        return {"status": "ok", "evidence": []}


@pytest.mark.parametrize("finish,expected_calls", [(None, 0), ("tool_calls", 1)])
def test_installed_codex_dispatches_only_terminal_tool_calls(tmp_path, finish, expected_calls):
    class Upstream(BaseHTTPRequestHandler):
        count = 0

        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()
            type(self).count += 1
            if type(self).count == 1:
                args = {key: "" for key in TOOLS["news_search"][1]}
                delta = {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "fixture-call",
                            "function": {"name": "news_search", "arguments": json.dumps(args)},
                        }
                    ]
                }
                chunks = [{"choices": [{"delta": delta, "finish_reason": None}]}]
                if finish:
                    chunks.append({"choices": [{"delta": {}, "finish_reason": finish}]})
            else:
                chunks = [
                    {
                        "choices": [
                            {"delta": {"content": "Fixture finished."}, "finish_reason": "stop"}
                        ]
                    }
                ]
            for chunk in chunks:
                self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
            self.wfile.write(b"data: [DONE]\n\n")

    config = json.loads(Path("research_room/local.example.json").read_text())
    settings = SimpleNamespace(
        codex_binary=Path(config["codex_binary"]),
        codex_sha256=config["codex_sha256"],
        profiles={"analyst": SimpleNamespace(model="fixture")},
    )
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    thread.start()
    gateway = StubGateway()
    bridge = Bridge({}, gateway.budget)
    bridge.allowed = {"news_search": TOOLS["news_search"]}
    port = bridge.start(0, "fixture", upstream.server_address[1])
    rpc = None
    try:
        rpc = RPC(settings, "analyst", port, tmp_path, gateway, threading.Event(), lambda *_: None)
        if expected_calls:
            rpc.turn("Execute the supplied fixture tool call.", timeout=20)
        else:
            with pytest.raises(RuntimeError, match="Codex turn failed"):
                rpc.turn("Execute the supplied fixture tool call.", timeout=20)
        assert len(gateway.calls) == expected_calls
        if expected_calls:
            assert gateway.calls[0]["tool"] == "news_search"
            assert gateway.calls[0]["arguments"] == {key: "" for key in TOOLS["news_search"][1]}
        assert Upstream.count == 1 + expected_calls
    finally:
        if rpc:
            rpc.close()
        bridge.close()
        upstream.shutdown()
        upstream.server_close()
        thread.join(timeout=3)
