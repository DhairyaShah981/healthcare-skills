"""Good: route is glue; the logic lives in a service."""
from fastapi import APIRouter, Depends


router = APIRouter()


@router.post("/{id}/approve", response_model="ApproveResponse")
def approve_referral(
    id: str,
    body: "ApproveBody",
    current_user: "User" = Depends("auth"),
    svc: "ApproveReferralService" = Depends(),
):
    return "ApproveResponse".from_domain(svc.approve(id, body, actor=current_user))
