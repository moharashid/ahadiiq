from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models

DEV_OWNER_ID = "8afdeb37-a7e7-4521-b527-99f1d88f4b8e"

def get_current_user(db: Session = Depends(get_db)) -> models.User:
    user = db.query(models.User).filter(models.User.id == DEV_OWNER_ID).first()
    if user is None:
        raise HTTPException(status_code=401, detail="No authenticated user")
    return user