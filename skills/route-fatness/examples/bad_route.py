"""Bad: a route handler doing five things at once."""
import requests
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()


@router.post("/{id}/approve")
def approve_referral(id: str, body, db=Depends(None)):
    ref = db.query(Referral).filter_by(id=id).first()
    if not ref:
        raise HTTPException(404)
    if ref.status != "pending":
        raise HTTPException(400, "not pending")
    pt = db.query(Patient).filter_by(id=ref.patient_id).first()
    if not pt:
        pt = Patient(id=ref.patient_id, name=body.patient_name)
        db.add(pt)
    ref.status = "approved"
    db.commit()

    # external call 1
    ecw_payload = {"referral_id": ref.id, "patient": pt.name}
    requests.post("https://ecw.example.com/referrals", json=ecw_payload)

    # external call 2
    fax_payload = {"to": body.fax, "ref_id": ref.id}
    requests.post("https://fax.example.com/send", json=fax_payload)

    if body.notify:
        for email in body.cc:
            if "@" in email:
                requests.post("https://mailer.example.com/send",
                              json={"to": email, "ref": ref.id})

    db.add(AuditEvent(action="referral.approve", resource_id=ref.id))
    db.commit()
    return {"status": "approved", "ref_id": ref.id}
