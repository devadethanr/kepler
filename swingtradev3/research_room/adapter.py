"""Adapted from the verified F bridge (see provenance.json).

Pinned text/function Responses subset; hosted/native tools are denied.
"""

import hashlib
import copy
import http.client
import http.server
import json
import select
import socket
import threading
import time
import uuid


class Bridge:
    def __init__(self, routes, budget):
        self.routes = routes
        self.budget = budget
        self.issued = {}
        self.outputs = {}
        self.lock = threading.Lock()
        self.allowed = {}
        self.tool_policy = None
        self.tool_constraints = None
        self.servers = []
        self.model_slots = {}

    def validate_arguments(self, name, args):
        if name not in self.allowed or not isinstance(args, dict):
            raise ValueError("Ungrantable function or non-object arguments")
        properties = self.allowed[name][1]
        if set(args) != set(properties):
            raise ValueError("Invalid argument keys")
        for key, schema in properties.items():
            value = args[key]
            if "enum" in schema and value not in schema["enum"]:
                raise ValueError("Argument outside granted enum")
            if schema["type"] == "string" and (not isinstance(value, str) or len(value) > 4096):
                raise ValueError("Invalid string argument")
            if schema["type"] == "integer" and (
                type(value) is not int
                or value < schema.get("minimum", -(2**31))
                or value > schema.get("maximum", 2**31)
            ):
                raise ValueError("Invalid integer argument")

    def translate(self, p, model):
        if p.get("model") != model:
            raise ValueError("unpinned model")
        tools = []
        for t in p.get("tools", []):
            if t.get("type") == "function" and t.get("name") in (
                "request_user_input",
                "view_image",
            ):
                continue
            if t.get("type") != "function" or t["name"] not in self.allowed:
                raise ValueError("ungranted tool type/name: " + str(t.get("name", t.get("type"))))
            tools.append(
                {
                    "type": "function",
                    "function": {k: t[k] for k in ("name", "description", "parameters") if k in t},
                }
            )
        granted = self.tool_policy(model) if self.tool_policy else set(self.allowed)
        tools = [t for t in tools if t["function"]["name"] in granted]
        if self.tool_constraints:
            constraints = self.tool_constraints(model)
            tools = copy.deepcopy(tools)
            for tool in tools:
                for field, choices in constraints.get(tool["function"]["name"], {}).items():
                    tool["function"]["parameters"]["properties"][field]["enum"] = choices
        system = []
        messages = []
        if p.get("instructions"):
            system.append(p["instructions"])
        source = p.get("input", [])
        if isinstance(source, str):
            source = [{"role": "user", "content": source}]
        for x in source:
            typ = x.get("type", "message")
            if typ == "reasoning":
                continue
            if typ == "function_call":
                with self.lock:
                    issued = self.issued.get(x["call_id"])
                if (
                    issued is None
                    or issued.get("model") != model
                    or issued["name"] != x["name"]
                    or (issued["arguments"] != x["arguments"])
                ):
                    raise ValueError("unknown/changed historical function call")
                messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": x["call_id"],
                                "type": "function",
                                "function": {"name": x["name"], "arguments": x["arguments"]},
                            }
                        ],
                    }
                )
            elif typ == "function_call_output":
                cid = x["call_id"]
                out = x.get("output", "")
                out = out if isinstance(out, str) else json.dumps(out)
                digest = hashlib.sha256(out.encode()).hexdigest()
                with self.lock:
                    if cid not in self.issued or self.issued[cid].get("model") != model:
                        raise ValueError("unmatched call_id/model")
                    if cid in self.outputs and self.outputs[cid] != digest:
                        raise ValueError("changed replay output")
                    self.outputs[cid] = digest
                messages.append({"role": "tool", "tool_call_id": cid, "content": out})
            elif typ == "message":
                content = x.get("content", "")
                if isinstance(content, list):
                    if any((y.get("type") not in ("input_text", "output_text") for y in content)):
                        raise ValueError("nontext content unsupported")
                    content = "\n".join((y.get("text", "") for y in content))
                role = x.get("role", "user")
                if role in ("system", "developer"):
                    system.append(content)
                elif role in ("user", "assistant"):
                    messages.append({"role": role, "content": content})
                else:
                    raise ValueError("unsupported role")
            else:
                raise ValueError("unsupported input type " + typ)
        if system:
            messages.insert(0, {"role": "system", "content": "\n\n".join(system)})
        chat = {
            "model": model,
            "messages": messages,
            "max_tokens": min(p.get("max_output_tokens", 512), 512),
            "temperature": 0,
            "stream": True,
            "stream_options": {"include_usage": True},
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if tools:
            chat.update(
                tools=tools,
                tool_choice="required"
                if granted == {"room_message"}
                else p.get("tool_choice", "auto"),
                parallel_tool_calls=False,
            )
        return chat

    def start(self, port, model, target):
        bridge = self
        model_slot = self.model_slots.setdefault(model, threading.Lock())

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                admitted = False
                slot_acquired = False
                usage = None
                conn = None
                done = threading.Event()
                seq = 0
                rid = "resp_" + uuid.uuid4().hex
                response = {
                    "id": rid,
                    "object": "response",
                    "created_at": int(time.time()),
                    "model": model,
                    "status": "in_progress",
                    "output": [],
                }

                def emit(kind, **kw):
                    nonlocal seq
                    obj = {"type": kind, "sequence_number": seq, **kw}
                    seq += 1
                    self.wfile.write(
                        ("event: " + kind + "\ndata: " + json.dumps(obj) + "\n\n").encode()
                    )
                    self.wfile.flush()

                try:
                    if self.path != "/v1/responses":
                        raise ValueError("route denied")
                    if int(self.headers.get("Content-Length", "0")) > 500000:
                        raise ValueError("oversize body")
                    payload = json.loads(
                        self.rfile.read(int(self.headers.get("Content-Length", "0")))
                    )
                    chat = bridge.translate(payload, model)
                    if not model_slot.acquire(blocking=False):
                        self.send_error(429, "Pinned model already has an active inference")
                        return
                    slot_acquired = True
                    if not bridge.budget.admit("model"):
                        self.send_error(429, "shared budget exhausted")
                        return
                    admitted = True
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    emit("response.created", response=response.copy())
                    emit("response.in_progress", response=response.copy())
                    conn = http.client.HTTPConnection("127.0.0.1", target, timeout=45)
                    conn.request(
                        "POST",
                        "/v1/chat/completions",
                        json.dumps(chat),
                        {"Content-Type": "application/json"},
                    )

                    def watch():
                        while not done.wait(0.05):
                            try:
                                readable, _, _ = select.select([self.connection], [], [], 0)
                                if readable and self.connection.recv(1, socket.MSG_PEEK) == b"":
                                    if conn.sock:
                                        conn.sock.shutdown(socket.SHUT_RDWR)
                                    conn.close()
                                    return
                            except OSError:
                                return

                    threading.Thread(target=watch, daemon=True).start()
                    upstream = conn.getresponse()
                    if upstream.status != 200:
                        raise RuntimeError(
                            "backend HTTP "
                            + str(upstream.status)
                            + ": "
                            + upstream.read().decode()[:500]
                        )
                    text = ""
                    calls = {}
                    message = None
                    usage = None
                    finish = None
                    for line in upstream:
                        if not line.startswith(b"data:"):
                            continue
                        data = line[5:].strip()
                        if data == b"[DONE]":
                            break
                        piece = json.loads(data)
                        if piece.get("usage"):
                            usage = piece["usage"]
                        if not piece.get("choices"):
                            continue
                        choice = piece["choices"][0]
                        delta = choice.get("delta", {})
                        if choice.get("finish_reason"):
                            finish = choice["finish_reason"]
                        chunk = delta.get("content") or ""
                        if chunk:
                            if message is None:
                                message = {
                                    "id": "msg_" + uuid.uuid4().hex,
                                    "type": "message",
                                    "role": "assistant",
                                    "status": "in_progress",
                                    "content": [],
                                }
                                emit(
                                    "response.output_item.added",
                                    output_index=0,
                                    item=message.copy(),
                                )
                                emit(
                                    "response.content_part.added",
                                    output_index=0,
                                    item_id=message["id"],
                                    content_index=0,
                                    part={"type": "output_text", "text": "", "annotations": []},
                                )
                            text += chunk
                            emit(
                                "response.output_text.delta",
                                output_index=0,
                                item_id=message["id"],
                                content_index=0,
                                delta=chunk,
                            )
                        for c in delta.get("tool_calls", []):
                            x = calls.setdefault(
                                c["index"], {"id": "", "name": "", "arguments": ""}
                            )
                            if c.get("id"):
                                x["id"] = c["id"]
                            x["name"] += c.get("function", {}).get("name", "")
                            x["arguments"] += c.get("function", {}).get("arguments", "")
                    output = []
                    if message:
                        part = {"type": "output_text", "text": text, "annotations": []}
                        message.update(status="completed", content=[part])
                        emit(
                            "response.output_text.done",
                            output_index=0,
                            item_id=message["id"],
                            content_index=0,
                            text=text,
                        )
                        emit(
                            "response.content_part.done",
                            output_index=0,
                            item_id=message["id"],
                            content_index=0,
                            part=part,
                        )
                        emit("response.output_item.done", output_index=0, item=message)
                        output.append(message)
                    if finish == "length" and calls:
                        raise ValueError("truncated tool call")
                    for c in calls.values():
                        if c["name"] not in bridge.allowed:
                            raise ValueError("model emitted ungranted tool")
                        args = json.loads(c["arguments"])
                        if not isinstance(args, dict):
                            raise ValueError("arguments must be object")
                        # Preserve the real model proposal. The capability gateway
                        # validates all argument keys/types before any action and
                        # returns a typed denial so Codex can repair malformed calls.
                        # Unknown function names remain a protocol-level failure.
                        c["id"] = c["id"] or "call_" + uuid.uuid4().hex
                        item = {
                            "type": "function_call",
                            "id": "fc_" + uuid.uuid4().hex,
                            "call_id": c["id"],
                            "name": c["name"],
                            "arguments": c["arguments"],
                            "status": "completed",
                        }
                        with bridge.lock:
                            if c["id"] in bridge.issued:
                                raise ValueError("duplicate backend call id")
                            bridge.issued[c["id"]] = {**c, "model": model}
                        idx = len(output)
                        emit(
                            "response.output_item.added",
                            output_index=idx,
                            item={**item, "arguments": "", "status": "in_progress"},
                        )
                        emit(
                            "response.function_call_arguments.delta",
                            output_index=idx,
                            item_id=item["id"],
                            delta=c["arguments"],
                        )
                        emit(
                            "response.function_call_arguments.done",
                            output_index=idx,
                            item_id=item["id"],
                            arguments=c["arguments"],
                        )
                        emit("response.output_item.done", output_index=idx, item=item)
                        output.append(item)
                    response.update(
                        output=output, status="incomplete" if finish == "length" else "completed"
                    )
                    if finish == "length":
                        response["incomplete_details"] = {"reason": "max_output_tokens"}
                    if usage:
                        response["usage"] = {
                            "input_tokens": usage.get("prompt_tokens", 0),
                            "output_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                        }
                    emit(
                        "response.incomplete" if finish == "length" else "response.completed",
                        response=response,
                    )
                except Exception as e:
                    if not admitted:
                        self.send_error(400, str(e))
                    else:
                        try:
                            response.update(
                                status="failed", error={"code": "server_error", "message": str(e)}
                            )
                            emit("response.failed", response=response)
                        except OSError:
                            pass
                finally:
                    done.set()
                    if conn:
                        conn.close()
                    if slot_acquired:
                        model_slot.release()
                    if admitted:
                        bridge.budget.release("model", response.get("usage"))

        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.servers.append(server)
        return server.server_address[1]

    def close(self):
        for s in self.servers:
            s.shutdown()
            s.server_close()
