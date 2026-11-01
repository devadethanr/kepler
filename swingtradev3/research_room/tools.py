"""Read-only, bounded capabilities. No arbitrary Cypher, shell, broker or credential tools."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import re
import stat
import threading
import time
from pathlib import Path

from .grounding import mentions_target, packet, validate_claims

STRING = {"type": "string"}


def _graph_child(pipe, name, value):
    """Run only the two fixed, bounded read operations in an owned process."""
    repository = None
    try:
        from context_graph.repository import ContextGraphRepository

        repository = ContextGraphRepository()
        if name == "graph_lookup":
            rows = repository._run(
                "MATCH (s:Stock {id: $id}) OPTIONAL MATCH (s)-[r]-(e) "
                "WHERE type(r) IN $rels AND any(l IN labels(e) WHERE l IN $labels) "
                "RETURN s.id AS stock_id, s.company_name AS company_name, "
                "e.id AS id, e.ticker AS ticker, e.title AS title, e.summary AS summary, "
                "e.lesson_text AS lesson_text, e.observed_at AS observed_at, "
                "type(r) AS relationship LIMIT 12",
                {
                    "id": "stock:" + value.upper(),
                    "rels": [
                        "AFFECTS_STOCK",
                        "MENTIONS",
                        "CANDIDATE_FOR",
                        "ABOUT_STOCK",
                        "APPLIES_TO_STOCK",
                    ],
                    "labels": ["NewsArticle", "ResearchCandidate", "Observation", "Lesson"],
                },
            )
        elif name == "graph_neighbors":
            rows = repository.get_graph_neighbors(
                value,
                allowed_labels=["Stock", "NewsArticle", "Observation", "ResearchCandidate"],
                limit=8,
            )
            rows = [{k: x[k] for k in ("source", "target", "relationship")} for x in rows]
        else:
            raise ValueError("Unknown graph operation")
        pipe.send((True, json.loads(json.dumps(rows, default=str))))
    except Exception as exc:
        pipe.send((False, type(exc).__name__))
    finally:
        if repository:
            repository.close()
        pipe.close()


def _supervised_graph(name, value, deadline, cancelled):
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_graph_child, args=(send, name, value))
    process.start()
    send.close()
    try:
        while True:
            if cancelled is not None and cancelled.is_set():
                raise TimeoutError("Research cancelled during graph read")
            if time.monotonic() >= deadline:
                raise TimeoutError("Graph read deadline exceeded")
            if receive.poll(min(0.1, max(0, deadline - time.monotonic()))):
                ok, result = receive.recv()
                if not ok:
                    raise RuntimeError("Graph read unavailable: " + result)
                return result
            if not process.is_alive():
                raise RuntimeError("Graph read process exited without a result")
    finally:
        receive.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join()


def _browser_excerpt(text, retrieval, offset):
    excerpt = text[offset : offset + 6000]
    return excerpt, {
        **retrieval,
        "offset": offset,
        "end_offset": offset + len(excerpt),
        "next_offset": offset + len(excerpt) if offset + len(excerpt) < len(text) else None,
        "truncated": retrieval["truncated"] or offset + len(excerpt) < len(text),
        "pagination": "page refetched; offsets can shift if content changes",
    }


TOOLS = {
    "graph_lookup": (
        "Look up scoped stock evidence in the actual current graph; historical as_of unsupported.",
        {"entity": STRING},
    ),
    "graph_neighbors": (
        "Read one bounded hop from a node returned by graph_lookup.",
        {"node_id": STRING},
    ),
    "artifact_search": (
        "Search approved research documents for target-relevant text.",
        {"query": STRING},
    ),
    "artifact_read": (
        "Read a relative approved research file. No private/config files.",
        {"path": STRING},
    ),
    "artifact_read_more": (
        "Read another bounded page of target-filtered text; offset is a character offset.",
        {"path": STRING, "offset": STRING},
    ),
    "artifact_search_more": (
        "Continue a bounded search from its next scan offset.",
        {"query": STRING, "offset": STRING},
    ),
    "skills_discover": ("Discover pinned skills before loading them.", {}),
    "skills_load": (
        "Load the complete pinned agent-browser skill before browser_read.",
        {"id": STRING},
    ),
    "browser_read": (
        "Read a public allowlisted URL using isolated agent-browser; no accounts.",
        {"url": STRING},
    ),
    "browser_read_more": (
        "Read a bounded later page of the captured public DOM body; offset is a character offset.",
        {"url": STRING, "offset": STRING},
    ),
    "room_message": (
        "Publish to your peer or room. text: <=60 public words. quote_id: a q: ID from retrieved quote_spans, or empty for a question/abstention. position: question/challenge continue research, conclude proposes a cited conclusion, agree explicitly supports the received peer message, disagree preserves an objection, abstain acknowledges insufficient evidence, revise publishes a cited revision.",
        {
            "recipient": {"type": "string", "enum": ["analyst", "skeptic", "room"]},
            "text": STRING,
            "quote_id": STRING,
            "claim_kind": {"type": "string", "enum": ["observation", "inference", "question"]},
            "support_assessment": {
                "type": "string",
                "enum": ["unassessed", "supported", "contradicted", "insufficient"],
            },
            "event_id": STRING,
            "position": {
                "type": "string",
                "enum": [
                    "question",
                    "challenge",
                    "conclude",
                    "agree",
                    "disagree",
                    "abstain",
                    "revise",
                ],
            },
        },
    ),
}


def specs():
    return [
        {
            "type": "function",
            "name": name,
            "description": desc,
            "deferLoading": False,
            "inputSchema": {
                "type": "object",
                "properties": props,
                "required": list(props),
                "additionalProperties": False,
            },
        }
        for name, (desc, props) in TOOLS.items()
    ]


class Gateway:
    def __init__(self, settings, store, room, owner, budget):
        self.settings, self.store, self.room = settings, store, room
        self.owner, self.budget = owner, budget
        self.root = settings.artifact_root.resolve(strict=True)
        self.evidence, self.nodes = {}, set()
        self.discovered, self.loaded = set(), set()
        self.lock = threading.RLock()
        self.graph = None
        self.turn_reads = {}
        self.published = set()
        self.delivered = {}

    def begin_turn(self, role):
        self.turn_reads[role] = 0
        self.published.discard(role)

    def granted_tools(self, role):
        if role in self.published:
            return set()
        if self.turn_reads.get(role, 0) >= 4:
            return {"room_message"}
        return set(TOOLS)

    def close(self):
        if self.graph:
            self.graph.close()

    @staticmethod
    def _offset(value, maximum):
        if not isinstance(value, str) or not value.isascii() or not value.isdigit():
            raise ValueError("Offset must be a non-negative decimal integer")
        offset = int(value)
        if offset > maximum:
            raise ValueError("Offset exceeds the bounded retrieval limit")
        return offset

    def _evidence(self, source, text, published=None, **metadata):
        item = packet(self.room["target"], source, text, published_at=published, **metadata)
        self.evidence[item["id"]] = item
        return item

    def _read(self, relative):
        path = Path(relative)
        if (
            path.is_absolute()
            or ".." in path.parts
            or any(x.startswith(".") for x in path.parts)
            or path.suffix.lower() not in (".md", ".txt", ".json", ".jsonl")
        ):
            raise ValueError("Path outside approved research artifacts")
        directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for component in path.parts[:-1]:
                next_directory = os.open(
                    component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
                )
                os.close(directory)
                directory = next_directory
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        except OSError as exc:
            raise ValueError("Artifact path cannot be opened without following links") from exc
        finally:
            os.close(directory)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 256000:
                raise ValueError("Artifact type/size refused")
            text = os.read(fd, 256001).decode("utf-8")
        finally:
            os.close(fd)
        # Return target-relevant paragraphs, including contradictions, rather than the full register.
        if self.room["target"].casefold() == self.settings.workspace_target.casefold():
            return text
        paragraphs = text.split("\n\n")
        selected = {
            i for i, block in enumerate(paragraphs) if mentions_target(block, self.room["target"])
        }
        # Adjacent paragraphs retain headings, qualifications and contradicting context.
        indices = {j for i in selected for j in range(max(0, i - 1), min(len(paragraphs), i + 3))}
        return "\n\n".join(paragraphs[i] for i in sorted(indices))

    def execute(self, role, params):
        name, args, cid = params["tool"], params["arguments"], params["callId"]
        args = json.loads(args) if isinstance(args, str) else args
        if name == "room_message" and isinstance(args, dict):
            args = {
                "claim_kind": "inference",
                "support_assessment": "unassessed",
                "event_id": "",
                **args,
            }
        if (
            name not in TOOLS
            or not isinstance(args, dict)
            or set(args) != set(TOOLS[name][1])
            or any(not isinstance(v, str) or len(v) > 4096 for v in args.values())
        ):
            output = {
                "status": "denied",
                "error": "Invalid or ungranted tool arguments",
                "expected_arguments": TOOLS[name][1] if name in TOOLS else {},
            }
            self.store.event(
                self.room["id"],
                self.owner,
                "rejected:" + cid,
                "tool.rejected",
                {"call_id": cid, "name": name, "output": output},
                role,
            )
            return output
        # The intent is persisted BEFORE the action. No ambiguous tool re-execution after a crash.
        with self.lock:
            previous = self.store.events(self.room["id"])
            for event in previous:
                if event["kind"] == "tool.result" and event["data"].get("call_id") == cid:
                    intent = next(
                        e
                        for e in previous
                        if e["kind"] == "tool.started" and e["data"].get("call_id") == cid
                    )
                    if (
                        intent["agent"] != role
                        or intent["data"]["name"] != name
                        or intent["data"]["arguments"] != args
                    ):
                        return {"status": "denied", "error": "Changed or cross-role tool replay"}
                    return event["data"]["output"]
            if any(
                e["kind"] == "tool.started" and e["data"].get("call_id") == cid for e in previous
            ):
                return {
                    "status": "unknown",
                    "error": "Unreconciled prior tool intent; not replayed",
                }
            repeats = sum(
                e["kind"] == "tool.started"
                and e["agent"] == role
                and e["data"]["name"] == name
                and e["data"]["arguments"] == args
                for e in previous
            )
            if repeats >= 2:
                from .store import RoomStopped

                raise RoomStopped("Repeated tool action without new evidence")
            if not self.budget.admit("tool"):
                return {"status": "denied", "error": "Room stopped or shared tool budget exhausted"}
            try:
                self.store.event(
                    self.room["id"],
                    self.owner,
                    "tool:" + cid,
                    "tool.started",
                    {
                        "call_id": cid,
                        "name": name,
                        "arguments": args,
                        "thread_id": params.get("threadId"),
                        "turn_id": params.get("turnId"),
                    },
                    role,
                )
                try:
                    output = self.dispatch(role, cid, name, args)
                except (ValueError, OSError) as exc:
                    output = {"status": "denied", "error": str(exc)}
                    if name == "room_message":
                        output["instruction"] = (
                            "Copy a quote_spans q:id into quote_id. If evidence is insufficient use position abstain and empty quote_id."
                        )
                        output["available_citations"] = [
                            {"evidence_id": e["id"], "quote_spans": e.get("quote_spans", [])[:4]}
                            for e in list(self.evidence.values())[-2:]
                        ]
                except Exception as exc:
                    output = {"status": "unavailable", "error": type(exc).__name__}
                self.store.event(
                    self.room["id"],
                    self.owner,
                    "result:" + cid,
                    "tool.result",
                    {"call_id": cid, "name": name, "output": output},
                    role,
                )
                if name != "room_message":
                    self.turn_reads[role] = self.turn_reads.get(role, 0) + 1
                return output
            finally:
                self.budget.release("tool")

    def dispatch(self, role, cid, name, args):
        target = self.room["target"]
        if name in ("graph_lookup", "graph_neighbors"):
            from config import cfg

            if not cfg.context_graph.enabled:
                raise RuntimeError("Context graph is disabled")
            if name == "graph_lookup":
                if args["entity"].casefold() != target.casefold():
                    raise ValueError("Cross-target lookup refused; create a separately scoped room")
                value = target
            else:
                value = args["node_id"]
                if value not in self.nodes:
                    raise ValueError(
                        "Traversal must start from evidence already retrieved in this room"
                    )
            remaining = max(0, self.room.get("deadline", time.time() + 30) - time.time())
            rows = _supervised_graph(
                name, value, time.monotonic() + min(30, remaining), getattr(self, "stop", None)
            )
            if name == "graph_lookup":
                self.nodes.update(x["id"] for x in rows if x.get("id"))
            if not rows:
                return {
                    "status": "empty",
                    "evidence": [],
                    "as_of": "current only",
                    "retrieval": {
                        "scope": name,
                        "completeness": "unknown; current graph projection only",
                    },
                }
            retrieval = {
                "scope": name,
                "result_limit": 12 if name == "graph_lookup" else 8,
                "returned": len(rows),
                "truncated": "unknown",
                "completeness": "unknown; current graph projection only",
            }
            return {
                "status": "ok",
                "evidence": [
                    self._evidence(
                        "graph:" + target, json.dumps(rows, default=str), retrieval=retrieval
                    )
                ],
                "retrieval": retrieval,
                "as_of": "current projection; historical/freshness completeness unproven",
            }
        if name in ("artifact_read", "artifact_read_more"):
            text = self._read(args["path"])
            offset = self._offset(args.get("offset", "0"), 256000)
            excerpt = text[offset : offset + 6000]
            retrieval = {
                "scope": "target-filtered document",
                "offset_basis": "filtered characters",
                "offset": offset,
                "end_offset": offset + len(excerpt),
                "truncated": offset + len(excerpt) < len(text),
                "next_offset": offset + len(excerpt) if offset + len(excerpt) < len(text) else None,
                "completeness": "filtered; unrelated paragraphs omitted",
            }
            return {
                "status": "ok" if excerpt else "empty",
                "retrieval": retrieval,
                "evidence": [self._evidence("file:" + args["path"], excerpt, retrieval=retrieval)]
                if excerpt
                else [],
            }
        if name in ("artifact_search", "artifact_search_more"):
            query = args["query"].strip().casefold()
            if not query or len(query) > 160:
                raise ValueError("Search query must be 1–160 characters")
            found = []
            offset = self._offset(args.get("offset", "0"), 10000)
            scanned = 0
            next_offset = None

            def paths():
                for directory, dirs, files in os.walk(self.root, followlinks=False):
                    dirs[:] = sorted(x for x in dirs if not x.startswith("."))
                    for filename in sorted(files):
                        if not filename.startswith("."):
                            yield Path(directory) / filename

            for i, p in enumerate(paths()):
                if i < offset:
                    continue
                if i >= 10000 or scanned >= 2000 or len(found) >= 6:
                    next_offset = i if i < 10000 else None
                    break
                scanned += 1
                if p.suffix.lower() not in (".md", ".txt", ".json", ".jsonl") or p.is_symlink():
                    continue
                try:
                    text = self._read(str(p.relative_to(self.root)))
                except (ValueError, OSError, UnicodeError):
                    continue
                terms = re.findall(r"[a-z0-9]+", query)
                if terms and all(term in text.casefold() for term in terms):
                    position = min(text.casefold().find(term) for term in terms)
                    start = max(0, position - 200)
                    snippet = text[start : position + 800]
                    details = {
                        "scope": "target-filtered search excerpt",
                        "offset_basis": "filtered characters",
                        "offset": start,
                        "end_offset": start + len(snippet),
                        "truncated": start > 0 or start + len(snippet) < len(text),
                        "completeness": "excerpt; surrounding and unrelated text omitted",
                    }
                    item = self._evidence(
                        "file:" + str(p.relative_to(self.root)), snippet, retrieval=details
                    )
                    item["path"] = str(p.relative_to(self.root))
                    found.append(item)
            return {
                "status": "ok" if found else "empty",
                "evidence": found,
                "retrieval": {
                    "scope": "approved target-filtered artifacts",
                    "query": query,
                    "scan_offset": offset,
                    "scanned": scanned,
                    "scan_limit": 2000,
                    "result_limit": 6,
                    "next_offset": next_offset,
                    "truncated": next_offset is not None or offset + scanned >= 10000,
                    "total_scan_cap": 10000,
                    "pagination": "live tree; offsets can shift if files change",
                    "completeness": "unknown; target filtering and unreadable files may omit evidence",
                },
            }
        if name == "skills_discover":
            self.discovered.add(role)
            return {
                "status": "ok",
                "skills": [
                    {
                        "id": "agent-browser",
                        "version": "0.41.0",
                        "commit": "5868f7c05020e047c00e68e4abf9253cce864f41",
                    }
                ],
            }
        if name == "skills_load":
            if args["id"] != "agent-browser" or role not in self.discovered:
                raise ValueError("Discover the pinned agent-browser skill first")
            core = self.settings.browser_skill.read_bytes()
            if hashlib.sha256(core).hexdigest() != self.settings.browser_skill_sha256:
                raise ValueError("Browser skill hash differs from pin")
            self.loaded.add(role)
            return {
                "status": "ok",
                "workflow": core.decode(),
                "sha256": self.settings.browser_skill_sha256,
                "enforced_capability": "browser_read only; read-only public allowlisted pages; no shell/login",
            }
        if name in ("browser_read", "browser_read_more"):
            if role not in self.loaded:
                raise ValueError("Discover and load agent-browser before browsing")
            from .browser import read_public_page

            text, final_url, retrieval = read_public_page(
                self.settings, args["url"], getattr(self, "stop", None), with_metadata=True
            )
            offset = self._offset(args.get("offset", "0"), 12000)
            excerpt, retrieval = _browser_excerpt(text, retrieval, offset)
            if not mentions_target(excerpt, target):
                return {
                    "status": "empty",
                    "reason": "No selected-target text in this excerpt",
                    "retrieval": retrieval,
                }
            return {
                "status": "ok",
                "retrieval": retrieval,
                "evidence": [self._evidence(final_url, excerpt, retrieval=retrieval)],
            }
        if name == "room_message":
            return self._message(role, cid, args)
        raise ValueError("Ungrantable tool")

    def _message(self, role, cid, args):
        target = self.room["target"]
        args = {
            "claim_kind": "inference",
            "support_assessment": "unassessed",
            "event_id": "",
            **args,
        }
        if args["claim_kind"] not in {"observation", "inference", "question"} or args[
            "support_assessment"
        ] not in {"unassessed", "supported", "contradicted", "insufficient"}:
            raise ValueError("Invalid claim kind or proposed support assessment")
        if args["recipient"] not in ({"analyst", "skeptic", "room"} - {role}):
            raise ValueError("Invalid addressed recipient")
        positions = {
            "question": ("question", "continue", "none"),
            "challenge": ("challenge", "continue", "objects"),
            "conclude": ("claim", "conclusion", "none"),
            "agree": ("synthesis", "conclusion", "supports"),
            "disagree": ("challenge", "disagreement", "objects"),
            "abstain": ("abstention", "abstention", "uncertain"),
            "revise": ("revision", "continue", "none"),
        }
        if args["position"] not in positions or not 1 <= len(args["text"].strip()) <= 1500:
            raise ValueError("Invalid position or public message size")
        kind, stance, assessment = positions[args["position"]]
        public = [e for e in self.store.events(self.room["id"]) if e["kind"] == "message"]
        if len(public) >= self.settings.max_messages:
            raise ValueError("Public message budget exhausted")
        prior = next((e for e in public if e["id"] == self.delivered.get(role)), None)
        if args["position"] == "agree" and not prior:
            raise ValueError("Agree requires a peer message delivered to this thread")
        inline = set(re.findall(r"\b(?:ev:[a-zA-Z0-9]+|q:[a-f0-9]+)", args["text"]))
        known_ids = set(self.evidence) | {
            q["id"] for e in self.evidence.values() for q in e.get("quote_spans", [])
        }
        if inline - known_ids:
            raise ValueError(
                "Unknown inline citation IDs; cite only retrieved evidence/quote spans"
            )
        selected = next(
            (
                e
                for e in self.evidence.values()
                if any(q["id"] == args["quote_id"] for q in e.get("quote_spans", []))
            ),
            None,
        )
        if args["quote_id"] and selected is None:
            raise ValueError("Unknown quoted span; copy a q:id from retrieved evidence")
        if args["event_id"] and (not selected or selected.get("event_id") != args["event_id"]):
            raise ValueError("Event identity is not established by this evidence")
        if args["support_assessment"] == "supported" and selected is None:
            raise ValueError("A proposed supported assessment requires a cited excerpt")
        claims = validate_claims(
            target,
            [{"evidence_id": selected["id"], "quote": args["quote_id"]}] if selected else [],
            self.evidence,
        )
        if (stance == "conclusion" or kind == "revision") and not claims:
            raise ValueError(
                "A conclusion/revision requires a quoted evidence span; otherwise abstain"
            )
        citation = claims[0] if claims else {}
        claim = {
            "id": "claim:" + hashlib.sha256(cid.encode()).hexdigest()[:16],
            "text": args["text"],
            "kind": args["claim_kind"],
            "target_entity": target,
            "entity_identity": "requested scope; source relevance unverified",
            "event_id": args["event_id"] or None,
            "evidence_refs": [{"evidence_id": selected["id"], "quote_id": args["quote_id"]}]
            if selected
            else [],
            "support_assessment": args["support_assessment"],
            "assessment_origin": "model proposal",
            "narrative_verification": "unassessed",
            "metadata_policy": selected.get("metadata_policy") if selected else None,
            "citation_admissibility": "admissible" if selected else "no citation",
            "source_metadata": {
                key: selected.get(key)
                for key in (
                    "record_id",
                    "event_id",
                    "published_at",
                    "event_at",
                    "fetched_at",
                    "decision_cutoff",
                    "adjustment",
                    "delay",
                    "retrieval",
                    "source_type",
                )
            }
            if selected
            else None,
            **citation,
        }
        data = {
            "sender": role,
            "recipient": args["recipient"],
            "kind": kind,
            "text": args["text"],
            "claims": [claim],
            "stance": stance,
            "validation": "exact citation spans verified; interpretation not fact-checked"
            if claims
            else "no cited facts verified; public interpretation only",
            "reply_to": prior["id"] if prior else None,
            "assessment": assessment if prior else "none",
        }
        event = self.store.event(
            self.room["id"], self.owner, "message:" + cid, "message", data, role
        )
        self.published.add(role)
        return {"status": "ok", "message_id": event["id"], "seq": event["seq"]}
