"""Ad deal management routes — list, approve, reject, view proposals."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..models import AdDeal
from ..schemas import AdDealRead, DealApproveRequest, DealRejectRequest

router = APIRouter(prefix="/admin/api/deals", tags=["deals"])


@router.get("/", response_model=List[AdDealRead])
def list_deals(
    status: str = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    q = db.query(AdDeal).order_by(AdDeal.created_at.desc())
    if status:
        q = q.filter(AdDeal.status == status)
    return q.limit(limit).all()


@router.get("/{deal_id}", response_model=AdDealRead)
def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    deal = db.query(AdDeal).get(deal_id)
    if not deal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/approve")
async def approve_deal(
    req: DealApproveRequest,
    _admin: str = Depends(verify_admin_token),
):
    from services.ad_manager import approve_deal as do_approve

    result = await do_approve(req.deal_id)
    return result


@router.post("/reject")
async def reject_deal(
    req: DealRejectRequest,
    _admin: str = Depends(verify_admin_token),
):
    from services.ad_manager import reject_deal as do_reject

    result = await do_reject(req.deal_id, req.reason)
    return result
