from abc import ABC, abstractmethod

class Queue(ABC):
    
    @abstractmethod
    def enqueue(self, job_id):
        pass
    
    @abstractmethod
    def consume(self):
        pass
    
    @abstractmethod
    def acknowledge(self, job_id):
        pass

