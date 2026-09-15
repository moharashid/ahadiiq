import time
from app import models 
from app.core.database import SessionLocal
from app.services.queue import database_queue
from app.services.ocr import textract_ocr_service
from app.services.extractor import anthropic_extractor
from datetime import date

def parse_date(value):
    return date.fromisoformat(value) if value else None

while True:
    db = SessionLocal()
    job = None
    print("Checking for pending jobs...")
    try:
        #1. consume a job from the queue  
        job = database_queue.consume(db)
        if job is not None:
            print(f"Processing job {job.id} for agreement {job.agreement_id}")
            
            #2. query the agreement to get the S3 key, and status
            agreement = db.query(models.Agreement).filter(models.Agreement.id == job.agreement_id).first() 
            agreement.status = "processing" 
            db.commit()  # persist the status change explicitly
    
            #3. call the ocr service to extract text from the S3 object
            result = textract_ocr_service.extract(agreement.storage_key)
            
            extracted_text = result.get("text")
            extracted_job_id = result.get("job_id")
            
            #4. store the extracted text in the database  
            extracted_job = models.ExtractedText(
                agreement_id=job.agreement_id,
                tenant_id=job.tenant_id,
                extracted_text=extracted_text,
                job_id=extracted_job_id
            )
            db.add(extracted_job)
            agreement.status = "extracted"  # update the agreement status to extracted
            db.commit()                    # persist the OCR result explicitly
            
            #5. call the AI extractor to extract structured data from the text
            structured_data = anthropic_extractor.extract(extracted_text)
            
            # 6. update the agreement record with the structured data
            agreement.agreement_type = structured_data.get("agreement_type")
            agreement.parties = structured_data.get("parties")
            agreement.signatories = structured_data.get("signatories")
            agreement.effective_date = parse_date(structured_data.get("effective_date"))
            agreement.expiry_date = parse_date(structured_data.get("expiry_date"))
           
            #7. update the clause records in the database
            clauses = structured_data.get("clauses", [])
            for clause in clauses:
                clause_record = models.Clause(
                    agreement_id=job.agreement_id,
                    tenant_id=job.tenant_id,
                    clause_type=clause.get("type"),
                    clause_text=clause.get("text"),
                    notice_period=clause.get("notice_period_days"),
                    relative_to=clause.get("relative_to"),
                    amount=clause.get("amount")
                )
                db.add(clause_record)
            db.commit()  # persist the clauses explicitly and the structured data to agreements explicitly
            
            # 8. mark the job as completed in the queue
            database_queue.acknowledge(db, job)
            print(f"Completed processing job {job.id}")
        else:
            print("No pending jobs found. Waiting for new jobs...")
            time.sleep(5)
    except Exception as e:
        print(f"Error occurred while processing job: {str(e)}")
        db.rollback()
        print(f"{str(e)}") 
        if job:
            job.status = "failed" 
            job.error_message = f"{str(e)}"
            db.commit()
            
    finally:
        db.close()   
