from abc import ABC, abstractmethod
from app.core.config import settings
import boto3
import logging
import time
logger = logging.getLogger(__name__)


class AIExtractor(ABC):
    @abstractmethod
    def extract(self, text: str):
        pass
    
class NovaExtractor(AIExtractor):
    def __init__(self):
        pass
    def extract(self, text: str):
        pass