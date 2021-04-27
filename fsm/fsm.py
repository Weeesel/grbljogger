
import sys

import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

from abc import ABC, abstractmethod


class State(ABC):
    @classmethod
    def enter(cls, **kwargs):
        """Will be executed before entering, return False to decline the transition."""
        return True
        
    @classmethod
    def entered(cls, **kwargs):
        """Will be executed after entering the state."""
        pass
        
    @classmethod
    def exit(cls, **kwargs):
        """Will be executed before leaving the state, return False to decline the transition."""
        return True
        
    @classmethod
    def exited(cls, **kwargs):
        """Will be executed after the transition into the new state, but before `entered()`."""
        pass
        
    @classmethod
    @abstractmethod
    def event(cls, **kwargs):
        """Handle event, return a `State` for a state transition or None to stay."""
        pass
        
        
class FSM:
    def __init__(self, init_state):
        if not init_state.enter():
            raise TypeError(f"Initial state {init_state.__name__} could not be set. {init_state.__name__}.enter() must return True.")
        self._state = init_state
        self._state.entered()
        
    def event(self, **kwargs):
        old_state = self._state
        new_state = self._state.event(**kwargs)
        if new_state is None:
            return
        if old_state.exit(**kwargs) and new_state.enter(**kwargs):
            self._state = new_state
            old_state.exited(**kwargs)
            new_state.entered(**kwargs)
        