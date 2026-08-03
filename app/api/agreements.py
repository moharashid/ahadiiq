from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy import text
from app.core.database import get_db
from sqlalchemy.orm import Session
from typing import Annotated
from app.services.storage import local_storage
from sqlalchemy.orm import Session
from app import models 
DEV_TENANT_ID = "f4cd81dd-afd4-4f3b-a636-9560dfd9c554"
DEV_OWNER_ID = "8afdeb37-a7e7-4521-b527-99f1d88f4b8e"

router = APIRouter()



@router.post('/upload_agreement')
async def upload_agreement(file: UploadFile, db: Session = Depends(get_db)):
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")
    storage_key = local_storage.save(await file.read(), file.filename)
    
    try:
        agreement = models.Agreement(
            filename=file.filename,
            storage_key=storage_key,
            status="uploaded",
            owner_id=DEV_OWNER_ID,
            tenant_id=DEV_TENANT_ID
        )
        db.add(agreement)
        db.flush()
        
        processing_job = models.ProcessingJob(
            agreement_id = agreement.id,
            tenant_id = agreement.tenant_id,
            status = "pending"     
        )
        db.add(processing_job)
        db.commit()
        db.refresh(agreement)
        db.refresh(processing_job)
        return {
            "message": "Agreement uploaded successfully and processing will begin shortly.",
            "agreement_id": str(agreement.id),
            "filename": agreement.filename,
            "storage_key": agreement.storage_key,
            "processing_status": processing_job.status
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save agreement metadata: {str(e)}")
    
    
            