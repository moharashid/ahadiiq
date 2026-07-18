from abc import ABC, abstractmethod
import os
import uuid

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
        
