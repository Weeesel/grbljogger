
from abc import ABC, abstractmethod
import contextlib
import logging

import serial
      
      
class Base(ABC):
    @abstractmethod
    def write(self, data): pass
    @abstractmethod
    def readline(self): pass
    @abstractmethod
    def read_all(self): pass
    
    
class Dummy(Base, contextlib.AbstractContextManager):
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        pass
    
    def write(self, data):
        logging.info(data)
        
    def readline(self):
        return b'ok\r\n'
        
    def read_all(self):
        return b'ok\r\n'
        
        
class Serial(serial.Serial, Base):
    pass