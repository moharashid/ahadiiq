from datetime import date
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.auth import get_current_user
from app import models
from app.schemas.dashboard_schema import ObligationOut, RiskOut
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
router = APIRouter()

class StatusUpdate(BaseModel):
    status: str


# --- 1. SUMMARY (the top tiles) ---
@router.get("/dashboard/summary")
def dashboard_summary(user: models.User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    today = date.today()

    agreements_q = db.query(models.Agreement).filter(
        models.Agreement.tenant_id == user.tenant_id)
    if user.role != "admin":
        agreements_q = agreements_q.filter(models.Agreement.owner_id == user.id)

    oblig_q = (db.query(models.Obligation)
               .join(models.Agreement, models.Obligation.agreement_id == models.Agreement.id)
               .filter(models.Obligation.tenant_id == user.tenant_id))
    if user.role != "admin":
        oblig_q = oblig_q.filter(models.Agreement.owner_id == user.id)

    return {
        "total_agreements":     agreements_q.count(),
        "pending_obligations":  oblig_q.filter(models.Obligation.status == "pending").count(),
        "overdue_obligations":  oblig_q.filter(models.Obligation.status != "completed",
                                               models.Obligation.due_date < today).count(),
        "high_risk_agreements": agreements_q.filter(models.Agreement.risk_level == "high").count(),
    }

# --- 2. OBLIGATIONS ---
@router.get("/obligations")
def list_obligations(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = (db.query(models.Obligation, models.Clause)
         .join(models.Agreement, models.Obligation.agreement_id == models.Agreement.id)
         .outerjoin(models.Clause, models.Obligation.clause_id == models.Clause.id)
         .filter(models.Obligation.tenant_id == user.tenant_id,
                 models.Obligation.status != "completed"))
    if user.role != "admin":
        q = q.filter(models.Agreement.owner_id == user.id)
    rows = q.order_by(models.Obligation.due_date.asc()).all()
    return [{
        "id": str(o.id), "agreement_id": str(o.agreement_id),
        "obligation_type": o.obligation_type, "status": o.status,
        "due_date": o.due_date.isoformat() if o.due_date else None,
        "clause_text": c.clause_text if c else None,
    } for o, c in rows]
# --- 3. RISKS ---
@router.get("/risks")
def list_risks(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = (db.query(models.Risk, models.Clause)
         .join(models.Agreement, models.Risk.agreement_id == models.Agreement.id)
         .outerjoin(models.Clause, models.Risk.clause_id == models.Clause.id)
         .filter(models.Risk.tenant_id == user.tenant_id,
                 models.Risk.status != "resolved"))
    if user.role != "admin":
        q = q.filter(models.Agreement.owner_id == user.id)
    rows = q.order_by(models.Risk.severity.desc()).all()
    return [{
        "id": str(r.id), "agreement_id": str(r.agreement_id),
        "risk_type": r.risk_type, "severity": r.severity,
        "description": r.description, "status": r.status,
        "clause_text": c.clause_text if c else None,
    } for r, c in rows]
    
    
@router.patch("/obligations/{obligation_id}")
def update_obligation(obligation_id: UUID, body: StatusUpdate,
                      user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.status not in ("pending", "completed"):
        raise HTTPException(400, "Invalid status")
    q = (db.query(models.Obligation)
         .join(models.Agreement, models.Obligation.agreement_id == models.Agreement.id)
         .filter(models.Obligation.id == obligation_id,
                 models.Obligation.tenant_id == user.tenant_id))
    if user.role != "admin":
        q = q.filter(models.Agreement.owner_id == user.id)
    obligation = q.first()
    if obligation is None:
        raise HTTPException(404, "Obligation not found")
    obligation.status = body.status
    db.commit()
    return {"id": str(obligation.id), "status": obligation.status}

@router.patch("/risks/{risk_id}")
def update_risk(risk_id: UUID, body: StatusUpdate,
                user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.status not in ("active", "resolved"):
        raise HTTPException(400, "Invalid status")
    q = (db.query(models.Risk)
         .join(models.Agreement, models.Risk.agreement_id == models.Agreement.id)
         .filter(models.Risk.id == risk_id, models.Risk.tenant_id == user.tenant_id))
    if user.role != "admin":
        q = q.filter(models.Agreement.owner_id == user.id)
    risk = q.first()
    if risk is None:
        raise HTTPException(404, "Risk not found")
    risk.status = body.status
    db.commit()
    return {"id": str(risk.id), "status": risk.status}