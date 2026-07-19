from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from app.core.database import get_db
from sqlalchemy.orm import Session



router = APIRouter()

@router.get('/health')
async def get_health():
    return {
        "status": "ok"
    }

@router.get('/health/db')
def db_health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status":"ok",
            "database":"connected"
        }
    except Exception:
        raise HTTPException(status_code=503, detail="database unreachable")
    