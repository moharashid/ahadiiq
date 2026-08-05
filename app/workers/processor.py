import time
from app import models 
from app.core.database import SessionLocal
from app.services.queue import database_queue


while True:
    db = SessionLocal()
    job = None
    print("Checking for pending jobs...")
    try:
        job = database_queue.consume(db)
        if job is not None:
            print(f"Processing job {job.id} for agreement {job.agreement_id}")
            time.sleep(15)
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
