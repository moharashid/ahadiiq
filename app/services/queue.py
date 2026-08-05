from abc import ABC, abstractmethod
from app import models
import datetime
class Queue(ABC):
    
    @abstractmethod
    def enqueue(self, db, agreement_id, tenant_id):
        pass
    
    @abstractmethod
    def consume(self, db):
        pass
    
    @abstractmethod
    def acknowledge(self, db, job):
        pass

class DatabaseQueue(Queue):
    def enqueue(self, db, agreement_id, tenant_id):
        job = models.ProcessingJob(
            agreement_id=agreement_id,
            tenant_id=tenant_id,
            status="pending")
        db.add(job)
        
        
    def consume(self, db):
        job = db.query(models.ProcessingJob).filter(models.ProcessingJob.status == "pending").with_for_update(skip_locked=True).first()
        if job:
            job.status = "processing"
            job.started_at = datetime.datetime.now().astimezone()
            db.commit()
        return job
    def acknowledge(self, db, job):
        job.status = "completed"
        job.completed_at = datetime.datetime.now().astimezone()
        db.commit()

database_queue = DatabaseQueue()