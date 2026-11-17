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
router = APIRouter()

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
@router.get("/obligations", response_model=List[ObligationOut])
def list_obligations(user: models.User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    q = (db.query(models.Obligation)
         .join(models.Agreement, models.Obligation.agreement_id == models.Agreement.id)
         .filter(models.Obligation.tenant_id == user.tenant_id))
    if user.role != "admin":
        q = q.filter(models.Agreement.owner_id == user.id)
    return q.order_by(models.Obligation.due_date.asc()).all()

# --- 3. RISKS ---
@router.get("/risks", response_model=List[RiskOut])
def list_risks(user: models.User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    q = (db.query(models.Risk)
         .join(models.Agreement, models.Risk.agreement_id == models.Agreement.id)
         .filter(models.Risk.tenant_id == user.tenant_id))
    if user.role != "admin":
        q = q.filter(models.Agreement.owner_id == user.id)
    return q.order_by(models.Risk.severity.desc()).all()