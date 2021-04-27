

from abc import ABC, abstractmethod
import contextlib

import keyboard


class Base(ABC):
    @abstractmethod
    def xyz(self): pass
    @abstractmethod
    def home_pressed(self): pass
    def rumble(self): pass

    
class Keyboard(Base, contextlib.AbstractContextManager):
    def xyz(self):
        def ax_val(neg, pos):
            return float(keyboard.is_pressed(pos)) - float(keyboard.is_pressed(neg))
        return ax_val('left', 'right'), ax_val('down', 'up'), ax_val('page down', 'page up')
        
    def __exit__(self, exc_type, exc_value, traceback):
        pass
    
    def home_pressed(self):
        return keyboard.is_pressed('h')
    
    def rumble(self):
        pass

        
try:
    from xbox360controller import Xbox360Controller

    class Xbox360(Base, contextlib.AbstractContextManager):
        def __init__(self, id=0):
            self._joystick = Xbox360Controller(0, axis_threshold=axis_threshold)
        
        def __enter__(self):
            self._joystick.__enter__()
            return self
        
        def __exit__(self, exc_type, exc_value, traceback):
            self._joystick.__exit__(exc_type, exc_value, traceback)
            
        def xyz(self):
            axy = self._joystick.axis_l
            az = self._joystick.axis_r
            def calc_threshold(value, threshold=axis_threshold):
                if value >= 0.0:
                    return 0.0 if value<threshold else (value-threshold)/(1-threshold)
                else:
                    return 0.0 if value>-threshold else (value+threshold)/(1-threshold)
            return tuple(map(calc_threshold, (axy.x, -axy.y, -az.y)))
        
        def rumble(self):
            self._joystick.set_rumble(0.333,0.333,200)
            
        def home_pressed(self):
            return self._joystick.button_start.is_pressed
            
except ModuleNotFoundError:
    pass