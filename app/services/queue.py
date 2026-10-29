from abc import ABC, abstractmethod
import json
from app import models
import boto3, os
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

class SQSQueue(Queue):
    def __init__(self, queue_url):
        self.sqs = boto3.client("sqs")
        self.queue_url = queue_url

    def enqueue(self, db, agreement_id, tenant_id):
        job = models.ProcessingJob(
                    agreement_id=agreement_id,
                    tenant_id=tenant_id,
                    status="pending")
        db.add(job)
        db.flush() # INSERT sent, job.id now populated — NOT committed yet
        
        try:
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(
                    {"job_id": str(job.id), 
                     "agreement_id": str(agreement_id), 
                     "tenant_id": str(tenant_id)
                     }) 
        )
        except Exception as e:
            db.rollback()  # undo the INSERT if SQS fails
            raise
        db.commit()  # commit the INSERT if SQS succeeds
        return job
    def consume(self, db):
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        )
        messages = response.get("Messages", [])
        if not messages:
            return None
        message = messages[0]
        job_data = json.loads(message["Body"])
        
        job = db.query(models.ProcessingJob).filter(models.ProcessingJob.id == job_data["job_id"]).with_for_update(skip_locked=True).first()
        if job is None:
            # If the job is not found in the database, delete the message from SQS to avoid reprocessing
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=message["ReceiptHandle"]
            )
            return None
        job.status = "processing"
        job.started_at = datetime.datetime.now().astimezone()
        db.commit()
        job._receipt_handle = message["ReceiptHandle"]
        return job
    def acknowledge(self, db, job):
        self.sqs.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=job._receipt_handle,   # must match the name you set in consume
        )
        job.status = "completed"
        job.completed_at = datetime.datetime.now().astimezone()
        db.commit()
        return job    
database_queue = DatabaseQueue()
sqs_queue = SQSQueue(queue_url=os.environ["QUEUE_URL"])