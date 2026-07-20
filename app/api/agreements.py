from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy import text
from app.core.database import get_db
from sqlalchemy.orm import Session
from typing import Annotated
from app.services.storage import local_storage
from sqlalchemy.orm import Session
from app.models.agreement import Agreement
from app.models.user import User
from app.models.tenant import Tenant

DEV_TENANT_ID = "b809ec79-ae62-4f41-9479-bd307ebeaf5c"
DEV_OWNER_ID = "530201ef-655a-4118-ab3f-687ce84b7865"

router = APIRouter()



@router.post('/upload_agreement')
async def upload_agreement(file: UploadFile, db: Session = Depends(get_db)):
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")
    storage_key = local_storage.save(await file.read(), file.filename)
    
    try:
        agreement = Agreement(
            filename=file.filename,
            storage_key=storage_key,
            agreement_type="default",
            status="uploaded",
            owner_id=DEV_OWNER_ID,
            tenant_id=DEV_TENANT_ID
        )
        db.add(agreement)
        db.commit()
        db.refresh(agreement)
        return {
            "message": "Agreement uploaded successfully.",
            "agreement_id": str(agreement.id),
            "filename": agreement.filename,
            "storage_key": agreement.storage_key
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save agreement metadata: {str(e)}")
    
    
            