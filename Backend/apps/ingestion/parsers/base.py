from abc import ABC, abstractmethod

class BaseParser(ABC):
    def __init__(self, upload_instance):
        self.upload = upload_instance
        
    @abstractmethod
    def parse(self):
        pass
        
    @abstractmethod
    def validate(self):
        pass
        
    @abstractmethod
    def normalise(self):
        pass
