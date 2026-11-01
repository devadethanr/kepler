"""Transactional room state + replay log in the existing cognition tables.

The report row is also the durable outbox. Streaming reads committed rows directly;
there is no lossy in-memory publish window or second authoritative state store.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from memory.db import session_scope
from memory.models import CognitionReportRow, CognitionRunRow

PHASE = "research_room_v1"
TERMINAL = {"conclusion", "disagreement", "abstention", "cancelled", "interrupted", "failed"}


class RoomStopped(RuntimeError):
    pass


class Store:
    def __init__(self, scope=session_scope):
        self.scope = scope

    def create(
        self,
        question: str,
        target: str,
        request_id: str,
        limits: dict,
        parent_room: str | None = None,
    ) -> dict:
        room_id = "room:" + str(uuid.UUID(request_id))
        with self.scope() as s:
            row = s.get(CognitionRunRow, room_id)
            if row:
                if row.payload["question"] != question or row.payload["target"] != target:
                    raise ValueError("Request ID already used for a different room")
                return self._view(row)
            row = CognitionRunRow(
                run_id=room_id,
                phase=PHASE,
                status="queued",
                started_at=datetime.now(timezone.utc),
                payload={
                    "parent_room": parent_room,
                    "question": question,
                    "target": target,
                    "seq": 0,
                    "limits": limits,
                    "counts": {
                        "model": 0,
                        "tool": 0,
                        "reserved_tokens": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "unknown_usage_calls": 0,
                    },
                    "active": {"model": 0, "tool": 0},
                },
            )
            s.add(row)
            s.flush()
            self._append(
                s, row, "created", "room.created", {"question": question, "target": target}
            )
            return self._view(row)

    @staticmethod
    def _view(row) -> dict:
        worker_state = "idle"
        if row.status == "running":
            worker_state = "active" if row.payload.get("lease_until", 0) >= time.time() else "stale"
        return {"id": row.run_id, "status": row.status, "worker_state": worker_state, **row.payload}

    @staticmethod
    def _row(s, room_id):
        row = s.scalar(
            select(CognitionRunRow)
            .where(CognitionRunRow.run_id == room_id, CognitionRunRow.phase == PHASE)
            .with_for_update()
        )
        if row is None:
            raise KeyError(room_id)
        return row

    @staticmethod
    def _fence(row, owner: str):
        if (
            row.status != "running"
            or row.payload.get("owner") != owner
            or row.payload.get("lease_until", 0) < time.time()
            or row.payload.get("deadline", 0) < time.time()
        ):
            raise RoomStopped("Room cancelled, lease lost, or deadline expired")

    @staticmethod
    def _append(s, row, key: str, kind: str, data: dict, agent: str = "manager") -> dict:
        event_id = row.run_id + ":" + hashlib.sha256(key.encode()).hexdigest()[:32]
        previous = s.get(CognitionReportRow, event_id)
        if previous:
            return previous.payload
        payload = dict(row.payload)
        seq = payload["seq"] + 1
        payload["seq"] = seq
        event = {
            "id": event_id,
            "room_id": row.run_id,
            "seq": seq,
            "kind": kind,
            "agent": agent,
            "at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        s.add(
            CognitionReportRow(
                report_id=event_id,
                run_id=row.run_id,
                agent_name=agent,
                schema_version="room.event.v1",
                status=kind,
                payload=event,
            )
        )
        row.payload = payload
        s.flush()
        return event

    def event(self, room_id, owner, key, kind, data, agent="manager") -> dict:
        with self.scope() as s:
            row = self._row(s, room_id)
            self._fence(row, owner)
            return self._append(s, row, key, kind, data, agent)

    def get(self, room_id) -> dict:
        with self.scope() as s:
            return self._view(self._row(s, room_id))

    def list(self) -> list[dict]:
        with self.scope() as s:
            rows = s.scalars(
                select(CognitionRunRow)
                .where(CognitionRunRow.phase == PHASE)
                .order_by(CognitionRunRow.started_at.desc())
                .limit(30)
            ).all()
            return [self._view(row) for row in rows]

    def events(self, room_id, after=0) -> list[dict]:
        with self.scope() as s:
            rows = s.scalars(
                select(CognitionReportRow)
                .where(
                    CognitionReportRow.run_id == room_id,
                    CognitionReportRow.schema_version == "room.event.v1",
                    CognitionReportRow.payload["seq"].as_integer() > after,
                )
                .order_by(CognitionReportRow.payload["seq"].as_integer())
                .limit(500)
            ).all()
            return [row.payload for row in rows]

    def claim(self, owner, lease_seconds):
        with self.scope() as s:
            rows = s.scalars(
                select(CognitionRunRow)
                .where(
                    CognitionRunRow.phase == PHASE,
                    CognitionRunRow.status.in_(["queued", "running", "cancelling"]),
                )
                .order_by(CognitionRunRow.started_at)
                .with_for_update(skip_locked=True)
            ).all()
            for row in rows:
                p = dict(row.payload)
                if row.status in ("running", "cancelling"):
                    if p.get("lease_until", 0) < time.time():
                        row.status = "interrupted" if row.status == "running" else "cancelled"
                        row.completed_at = datetime.now(timezone.utc)
                        self._append(
                            s,
                            row,
                            "lease.expired",
                            "room.finished",
                            {
                                "status": row.status,
                                "reason": "Worker lease expired; no tool replay",
                            },
                        )
                    continue
                p.update(
                    owner=owner,
                    lease_until=time.time() + lease_seconds,
                    deadline=time.time() + p["limits"]["seconds"],
                )
                row.payload = p
                row.status = "running"
                self._append(s, row, "claimed", "room.started", {"owner": owner})
                return self._view(row)
        return None

    def heartbeat(self, room_id, owner, lease_seconds):
        with self.scope() as s:
            row = self._row(s, room_id)
            self._fence(row, owner)
            row.payload = {**row.payload, "lease_until": time.time() + lease_seconds}

    def admit(self, room_id, owner, kind):
        with self.scope() as s:
            row = self._row(s, room_id)
            self._fence(row, owner)
            p = dict(row.payload)
            counts, active = dict(p["counts"]), dict(p["active"])
            limits = p["limits"]
            if counts[kind] >= limits[kind] or active[kind] >= (2 if kind == "model" else 1):
                raise RoomStopped("Shared room call/concurrency budget exhausted")
            counts[kind] += 1
            if kind == "model":
                counts["reserved_tokens"] += 32768
                if counts["reserved_tokens"] > limits["model"] * 32768:
                    raise RoomStopped("Shared room token reservation exhausted")
            active[kind] += 1
            row.payload = {**p, "counts": counts, "active": active}
            self._append(
                s,
                row,
                f"admit:{kind}:{counts[kind]}",
                "budget.admitted",
                {"kind": kind, "count": counts[kind], "reserved_tokens": counts["reserved_tokens"]},
            )

    def release(self, room_id, owner, kind, usage=None):
        with self.scope() as s:
            row = self._row(s, room_id)
            if row.payload.get("owner") != owner:
                return
            p = dict(row.payload)
            counts, active = dict(p["counts"]), dict(p["active"])
            active[kind] = max(0, active[kind] - 1)
            if kind == "model":
                if usage is None:
                    counts["unknown_usage_calls"] += 1
                else:
                    counts["input_tokens"] += usage.get("input_tokens", 0)
                    counts["output_tokens"] += usage.get("output_tokens", 0)
            row.payload = {**p, "counts": counts, "active": active}

    def cancel(self, room_id):
        with self.scope() as s:
            row = self._row(s, room_id)
            if row.status not in TERMINAL:
                row.status = "cancelled" if row.status == "queued" else "cancelling"
                self._append(s, row, "cancel", "room.cancel_requested", {})
            return self._view(row)

    def finish(self, room_id, owner, status, reason):
        with self.scope() as s:
            row = self._row(s, room_id)
            if row.payload.get("owner") != owner or row.status in TERMINAL:
                return
            if row.status == "cancelling":
                status, reason = "cancelled", "Operator cancelled research"
            row.status = status
            row.completed_at = datetime.now(timezone.utc)
            self._append(s, row, "finished", "room.finished", {"status": status, "reason": reason})


class Budget:
    """Durable admission adapter for the proven bridge. Reservation != actual usage.

    Whole-context reservations are cumulative and never refunded, including failures.
    Actual reported usage is stored separately; missing/error usage is explicitly unknown.
    """

    def __init__(self, store, room_id, owner):
        self.store, self.room_id, self.owner = store, room_id, owner

    def admit(self, kind):
        try:
            self.store.admit(self.room_id, self.owner, kind)
            return True
        except RoomStopped:
            return False

    def release(self, kind, usage=None):
        self.store.release(self.room_id, self.owner, kind, usage)
