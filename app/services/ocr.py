from abc import ABC, abstractmethod
import boto3
import logging
import time
logger = logging.getLogger(__name__)


class OCRService(ABC):
    @abstractmethod
    def extract(self, key: str):
        pass
    

class TextractOCR(OCRService):
    def __init__(self, bucket_name: str):
        self.textract_client = boto3.client('textract')
        self.bucket_name = bucket_name
        
    def extract(self, key: str):
        try:
            # phase1: Start the text detection job
            response = self.textract_client.start_document_text_detection(
                 DocumentLocation={

                    'S3Object': {
                        'Bucket': self.bucket_name,
                        'Name': key
                    }
                 }
            )
            job_id = response['JobId']
            logger.info(f"Started text detection job with JobId: {job_id} for S3 object {key}")
            # phase2 : poll for the job completion and on success, BREAK (don't return yet)
            while True:
                job = self.textract_client.get_document_text_detection(JobId=job_id)
                status = job['JobStatus']
                if status in ['SUCCEEDED', 'FAILED']:
                    if status == 'SUCCEEDED':
                        logger.info(f"Text detection job {job_id} completed successfully.")
                        break
                    if status == 'FAILED':
                        logger.error(f"Text detection job {job_id} failed.")
                        raise Exception(f"Textract job {job_id} failed")
                logger.info(f"Waiting for job {job_id} to complete. Current status: {status}")
                time.sleep(5) 
            
            # phase 3a: collect ALL blocks across all pages
            blocks = []
            next_token = None
            while True:
                if next_token:
                    result = self.textract_client.get_document_text_detection(JobId=job_id, NextToken=next_token)
                else:
                    result = self.textract_client.get_document_text_detection(JobId=job_id)
                blocks.extend(result['Blocks'])     # add this page's blocks to the pile
                next_token = result.get('NextToken')  # .get() returns None if no more pages
                if not next_token:
                    break       # no more pages, done  
            # phase 3b: pull the actual text out of the LINE blocks
            lines = [b['Text'] for b in blocks if b['BlockType'] == 'LINE']
            text = "\n".join(lines) 
            return text              
        except Exception as e:
            logger.error(f"Error occurred while extracting text from S3 object {key}: {e}")
            raise
        
    

   
   
