from abc import ABC, abstractmethod
import os
import uuid
import boto3
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class Storage(ABC):
    @abstractmethod
    def save(self, file: bytes, filename: str):
        pass

    @abstractmethod
    def get(self, key: str):
        pass


class LocalStorage(Storage):
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def save(self, file: bytes, filename: str):
        key = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(self.storage_dir, key)
        with open(file_path, 'wb') as f:
            f.write(file)
        return key    
    
    def get(self, key: str):
        file_path = os.path.join(self.storage_dir, key)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File with key {key} not found.")
        with open(file_path, 'rb') as f:
            return f.read()

class S3Storage(Storage):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        
    def save(self, file: bytes, filename: str):
        key = f"{uuid.uuid4()}_{filename}"
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name, 
                Key=key, 
                Body=file
                )
            return key
        
        except Exception as e:
            logger.error(f"Error occurred while saving file to S3: {e}")
            raise 

    def get(self, key: str):
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name, 
                Key=key
            )
            return response['Body'].read()
        except Exception as e:
            logger.error(f"Error occurred while retrieving file from S3: {e}")
            raise 

local_storage = LocalStorage(storage_dir="storage")

s3_storage = S3Storage(bucket_name=settings.s3_bucket_name)