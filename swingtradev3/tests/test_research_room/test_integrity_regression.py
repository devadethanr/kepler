"""Loopback SSE and disposable SQLite integrity regressions; no model or network provider."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from research_room.adapter import Bridge


class Budget:
    model_roles = {"fixture": "analyst"}
    usage = None

    def admit(self, *_args, **_kwargs):
        return True

    def release(self, _kind, usage):
        self.usage = usage


@pytest.mark.parametrize(
    "tool,finish,done,expected",
    [
        (False, None, False, "failed"),
        (False, None, True, "failed"),
        (True, None, False, "failed"),
        (True, "unknown", True, "failed"),
        (True, "length", True, "failed"),
        (True, "stop", True, "failed"),
        (False, "stop", True, "completed"),
        (False, "length", True, "incomplete"),
        (True, "tool_calls", True, "completed"),
    ],
)
def test_stream_requires_valid_terminal_before_item_done(tool, finish, done, expected):
    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()
            delta = (
                {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call-real",
                            "function": {"name": "lookup", "arguments": '{"entity":"ACME"}'},
                        }
                    ]
                }
                if tool
                else {"content": "fixture text"}
            )
            chunks = [{"choices": [{"delta": delta, "finish_reason": None}]}]
            if finish:
                chunks.append({"choices": [{"delta": {}, "finish_reason": finish}]})
            chunks.append(
                {
                    "choices": [],
                    "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
                }
            )
            for chunk in chunks:
                self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
            if done:
                self.wfile.write(b"data: [DONE]\n\n")

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    thread.start()
    budget = Budget()
    bridge = Bridge({}, budget)
    bridge.allowed = {"lookup": ("fixture", {"entity": {"type": "string"}})}
    port = bridge.start(0, "fixture", upstream.server_address[1])
    try:
        payload = {"model": "fixture", "input": "fixture"}
        request = Request(
            f"http://127.0.0.1:{port}/v1/responses",
            json.dumps(payload).encode(),
            {"Content-Type": "application/json"},
        )
        with build_opener(ProxyHandler({})).open(request, timeout=5) as response:
            events = [
                json.loads(line[6:])
                for line in response.read().decode().splitlines()
                if line.startswith("data: ")
            ]
        terminal = events[-1]
        assert terminal["type"] == "response." + expected
        assert terminal["response"]["usage"]["total_tokens"] == 6
        if expected == "failed":
            assert not any(e["type"] == "response.output_item.done" for e in events)
            assert not bridge.issued
            if tool:
                with pytest.raises(ValueError, match="unknown/changed"):
                    bridge.translate(
                        {
                            "model": "fixture",
                            "input": [
                                {
                                    "type": "function_call",
                                    "call_id": "call-real",
                                    "name": "lookup",
                                    "arguments": '{"entity":"ACME"}',
                                }
                            ],
                        },
                        "fixture",
                    )
        if tool and expected == "completed":
            assert terminal["response"]["output"][0]["call_id"] == "call-real"
            assert bridge.issued["call-real"]["model"] == "fixture"
            translated = bridge.translate(
                {
                    "model": "fixture",
                    "input": [
                        {
                            "type": "function_call",
                            "call_id": "call-real",
                            "name": "lookup",
                            "arguments": '{"entity":"ACME"}',
                        }
                    ],
                },
                "fixture",
            )
            assert translated["messages"][0]["tool_calls"][0]["id"] == "call-real"
        if expected == "incomplete":
            assert terminal["response"]["output"][0]["status"] == "incomplete"
            done_item = next(e for e in events if e["type"] == "response.output_item.done")
            assert done_item["item"]["status"] == "incomplete"
        assert budget.usage["total_tokens"] == 6
    finally:
        bridge.close()
        upstream.shutdown()
        upstream.server_close()
        thread.join(timeout=3)


def _events(port, model="fixture"):
    request = Request(
        f"http://127.0.0.1:{port}/v1/responses",
        json.dumps({"model": model, "input": "fixture"}).encode(),
        {"Content-Type": "application/json"},
    )
    with build_opener(ProxyHandler({})).open(request, timeout=5) as response:
        return [
            json.loads(line[6:])
            for line in response.read().decode().splitlines()
            if line.startswith("data: ")
        ]


def test_upstream_error_after_finish_rejects_tool():
    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()
            for chunk in [
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "x",
                                        "function": {"name": "lookup", "arguments": "{}"},
                                    }
                                ]
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                },
                {"error": {"message": "backend failed"}},
            ]:
                self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    bridge = Bridge({}, Budget())
    bridge.allowed = {"lookup": ("fixture", {})}
    port = bridge.start(0, "fixture", upstream.server_address[1])
    try:
        events = _events(port)
        assert events[-1]["type"] == "response.failed"
        assert not bridge.issued
        assert not any(e["type"] == "response.output_item.done" for e in events)
    finally:
        bridge.close()
        upstream.shutdown()
        upstream.server_close()


@pytest.mark.parametrize("failure", ["non200", "connection", "denied"])
def test_failure_releases_slot_and_accounts_admission(failure):
    class CountingBudget(Budget):
        model_roles = {"fixture": "analyst"}
        last_denial = "fixture denied"

        def __init__(self):
            self.admissions = 0
            self.releases = []

        def admit(self, *_args, **_kwargs):
            if failure == "denied":
                return False
            self.admissions += 1
            return True

        def denial_for(self, _role):
            return None

        def release(self, kind, usage):
            self.releases.append((kind, usage))

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(503)
            self.end_headers()

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    target = upstream.server_address[1]
    if failure == "connection":
        upstream.server_close()
    else:
        threading.Thread(target=upstream.serve_forever, daemon=True).start()
    budget = CountingBudget()
    bridge = Bridge({}, budget)
    port = bridge.start(0, "fixture", target)
    try:
        for _ in range(2):
            assert _events(port)[-1]["type"] == "response.failed"
        assert budget.admissions == (0 if failure == "denied" else 2)
        assert budget.releases == ([] if failure == "denied" else [("model", None)] * 2)
    finally:
        bridge.close()
        if failure != "connection":
            upstream.shutdown()
            upstream.server_close()


def test_duplicate_ids_across_concurrent_models_are_reserved_atomically():
    barrier = threading.Barrier(2)

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()
            barrier.wait(timeout=3)
            chunk = {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "shared",
                                    "function": {"name": "lookup", "arguments": "{}"},
                                }
                            ]
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            }
            self.wfile.write(("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode())

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    bridge = Bridge({}, Budget())
    bridge.allowed = {"lookup": ("fixture", {})}
    ports = [bridge.start(0, model, upstream.server_address[1]) for model in ("a", "b")]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda pair: _events(*pair), zip(ports, ("a", "b"))))
        assert sorted(events[-1]["type"] for events in results) == [
            "response.completed",
            "response.failed",
        ]
        failed = next(events for events in results if events[-1]["type"] == "response.failed")
        assert not any(e["type"] == "response.output_item.done" for e in failed)
        assert len(bridge.issued) == 1
    finally:
        bridge.close()
        upstream.shutdown()
        upstream.server_close()
