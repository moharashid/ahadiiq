from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy import text
from app.core.database import get_db
from sqlalchemy.orm import Session
from typing import Annotated
from app.services.storage import local_storage, s3_storage
from sqlalchemy.orm import Session
from app import models 
from app.services.queue import database_queue
from app.api.auth import get_current_user
from typing import List
from app.schemas.agreement import AgreementOut
import os
from uuid import UUID
import boto3
from fastapi.responses import RedirectResponse
from app.core.config import settings
# from app.services.queue import database_queue, sqs_queue
router = APIRouter()


@router.post('/upload_agreement')
async def upload_agreement(file: UploadFile, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")
    storage_key = s3_storage.save(await file.read(), file.filename)

    # 1) save the agreement first, on its own
    try:
        agreement = models.Agreement(
            filename=file.filename,
            storage_key=storage_key,
            status="uploaded",
            owner_id=user.id,
            tenant_id=user.tenant_id,
        )
        db.add(agreement)
        db.commit()            # durable BEFORE we try to queue
        db.refresh(agreement)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save agreement: {e}")

    # 2) queue it — enqueue owns its own commit/rollback for the JOB only
    try:
        database_queue.enqueue(db, agreement_id=agreement.id, tenant_id=user.tenant_id)
    except Exception as e:
        # agreement is saved; only queueing failed — surface it honestly
        raise HTTPException(status_code=502, detail=f"Agreement saved but queueing failed: {e}")

    return {
        "message": "Agreement uploaded successfully and processing will begin shortly.",
        "agreement_id": str(agreement.id),
        "filename": agreement.filename,
        "storage_key": agreement.storage_key,
    }
        
@router.get("/agreements", response_model=List[AgreementOut])
def list_agreements(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Agreement).filter(
        models.Agreement.tenant_id == user.tenant_id      # Layer 1: always
    )
    if user.role != "admin":
        query = query.filter(
            models.Agreement.owner_id == user.id          # Layer 2: members only
        )
    return query.all()
@router.get("/agreements/{agreement_id}", response_model=AgreementOut)
def get_agreement(agreement_id,
                  user: models.User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    q = db.query(models.Agreement).filter(
        models.Agreement.id == agreement_id,
        models.Agreement.tenant_id == user.tenant_id)
    if user.role != "admin":
        q = q.filter(models.Agreement.owner_id == user.id)
    agreement = q.first()
    if agreement is None:
        raise HTTPException(404, "Agreement not found")
    return agreement

@router.get("/agreements/{agreement_id}/detail")
def agreement_detail(agreement_id: UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.Agreement).filter(models.Agreement.id == agreement_id, models.Agreement.tenant_id == user.tenant_id)
    if user.role != "admin":
        q = q.filter(models.Agreement.owner_id == user.id)
    a = q.first()
    if a is None:
        raise HTTPException(404, "Agreement not found")
    obl = (db.query(models.Obligation, models.Clause)
           .outerjoin(models.Clause, models.Obligation.clause_id == models.Clause.id)
           .filter(models.Obligation.agreement_id == agreement_id)
           .order_by(models.Obligation.due_date.asc()).all())
    rsk = (db.query(models.Risk, models.Clause)
           .outerjoin(models.Clause, models.Risk.clause_id == models.Clause.id)
           .filter(models.Risk.agreement_id == agreement_id)
           .order_by(models.Risk.severity.desc()).all())
    return {
        "id": str(a.id), "filename": a.filename, "agreement_type": a.agreement_type,
        "status": a.status, "risk_level": a.risk_level, "risk_score": a.risk_score,
        "expiry_date": a.expiry_date.isoformat() if a.expiry_date else None,
        "parties": a.parties, "signatories": a.signatories,
        "obligations": [{"id": str(o.id), "obligation_type": o.obligation_type, "status": o.status,
                         "due_date": o.due_date.isoformat() if o.due_date else None,
                         "clause_text": c.clause_text if c else None} for o, c in obl],
        "risks": [{"id": str(r.id), "risk_type": r.risk_type, "severity": r.severity, "status": r.status,
                   "description": r.description, "clause_text": c.clause_text if c else None} for r, c in rsk],
    }

@router.get("/agreements/{agreement_id}/download")
def download_agreement(agreement_id: UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.Agreement).filter(models.Agreement.id == agreement_id, models.Agreement.tenant_id == user.tenant_id)
    if user.role != "admin":
        q = q.filter(models.Agreement.owner_id == user.id)
    a = q.first()
    if a is None:
        raise HTTPException(404, "Agreement not found")
    s3 = boto3.client("s3", region_name=settings.aws_region)
    url = s3.generate_presigned_url("get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": a.storage_key,
                "ResponseContentDisposition": f'attachment; filename="{a.filename}"'},
        ExpiresIn=300)
    return RedirectResponse(url)