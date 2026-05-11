from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from policy.bounds import PolicyValidationError
from policy.effective_policy import resolve_effective_policy
from policy.governor import PolicyGovernor

router = APIRouter()


class PolicyOverlayCreateBody(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    value: Any
    reason: str = Field(..., min_length=1, max_length=300)
    proposer: str = Field("operator", min_length=1, max_length=128)
    expires_at: str | None = None
    overlay_id: str | None = None
    rollback_handle: str | None = None


class PolicyOverlayApproveBody(BaseModel):
    approver: str = Field("operator", min_length=1, max_length=128)
    reason: str | None = None


class PolicyOverlayTerminalBody(BaseModel):
    actor: str = Field("operator", min_length=1, max_length=128)
    reason: str = Field(..., min_length=1, max_length=300)


def _validation_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/effective")
async def get_effective_policy() -> dict[str, Any]:
    return resolve_effective_policy().model_dump(mode="json")


@router.get("/overlays")
async def list_policy_overlays(
    status: str | None = None,
    key: str | None = None,
) -> list[dict[str, Any]]:
    try:
        overlays = PolicyGovernor().list_overlays(status=status, key=key)
    except PolicyValidationError as exc:
        raise _validation_error(exc) from exc
    return [overlay.model_dump(mode="json") for overlay in overlays]


@router.get("/overlays/{overlay_id}")
async def get_policy_overlay(overlay_id: str) -> dict[str, Any]:
    overlay = PolicyGovernor().get_overlay(overlay_id)
    if overlay is None:
        raise HTTPException(status_code=404, detail="policy overlay not found")
    return overlay.model_dump(mode="json")


@router.post("/overlays", status_code=status.HTTP_201_CREATED)
async def post_policy_overlay(body: PolicyOverlayCreateBody) -> dict[str, Any]:
    try:
        overlay = PolicyGovernor().propose_overlay(
            key=body.key,
            value=body.value,
            reason=body.reason,
            proposer=body.proposer,
            expires_at=body.expires_at,
            overlay_id=body.overlay_id,
            rollback_handle=body.rollback_handle,
        )
    except PolicyValidationError as exc:
        raise _validation_error(exc) from exc
    return overlay.model_dump(mode="json")


@router.post("/overlays/{overlay_id}/approve")
async def post_policy_overlay_approve(
    overlay_id: str,
    body: PolicyOverlayApproveBody,
) -> dict[str, Any]:
    try:
        overlay = PolicyGovernor().approve_overlay(
            overlay_id,
            approver=body.approver,
            reason=body.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="policy overlay not found") from exc
    except PolicyValidationError as exc:
        raise _validation_error(exc) from exc
    return overlay.model_dump(mode="json")


@router.post("/overlays/{overlay_id}/reject")
async def post_policy_overlay_reject(
    overlay_id: str,
    body: PolicyOverlayTerminalBody,
) -> dict[str, Any]:
    try:
        overlay = PolicyGovernor().reject_overlay(
            overlay_id,
            actor=body.actor,
            reason=body.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="policy overlay not found") from exc
    except PolicyValidationError as exc:
        raise _validation_error(exc) from exc
    return overlay.model_dump(mode="json")


@router.post("/overlays/{overlay_id}/rollback")
async def post_policy_overlay_rollback(
    overlay_id: str,
    body: PolicyOverlayTerminalBody,
) -> dict[str, Any]:
    try:
        overlay = PolicyGovernor().rollback_overlay(
            overlay_id,
            actor=body.actor,
            reason=body.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="policy overlay not found") from exc
    except PolicyValidationError as exc:
        raise _validation_error(exc) from exc
    return overlay.model_dump(mode="json")
