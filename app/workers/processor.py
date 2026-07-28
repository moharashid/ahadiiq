import time
from app.models.agreement import Agreement
from app.models.tenant import Tenant
from app.models.user import User
from app.core.database import SessionLocal
from app.models.process_jobs import ProcessingJob
import datetime

while True:
    db = SessionLocal()
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.status == "pending").first() 
        if job:
            job.status = "processing"
            job.started_at = datetime.datetime.now().astimezone()
            print(f"{job.id} processing")
            db.commit()
            time.sleep(15)
            job.status = "completed"
            job.completed_at = datetime.datetime.now().astimezone()
            print(f"{job.id} completed")
            db.commit()
        else:
            print(f"No jobs for now")
            time.sleep(5) 
    
    except Exception as e:
        db.rollback()
        print(f"{str(e)}") 
        if job:
            job.status = "failed" 
            job.error_message = f"{str(e)}"
            db.commit()
            
    finally:
        db.close()   
