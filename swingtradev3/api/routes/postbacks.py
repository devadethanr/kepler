from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from broker.postbacks import verify_postback_checksum
from broker.reducer import BrokerReducer


router = APIRouter()
reducer = BrokerReducer()


@router.post("/kite")
async def ingest_kite_postback(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid postback payload")
    if not verify_postback_checksum(payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid postback checksum")
    result = reducer.apply_order_update(payload, source="postback")
    return {"status": "ok", "reducer": result}
