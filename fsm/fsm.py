
import sys

import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

from abc import ABC, abstractmethod


class State(ABC):
    @classmethod
    def enter(cls, **kwargs):
        """Will be executed after entering."""
        
    @classmethod
    def exit(cls, **kwargs):
        """Will be executed before leaving the state."""
        
    @classmethod
    @abstractmethod
    def next(cls, **kwargs):
        """Return the next state for a transition or None to stay in this state."""
        pass
        
        
class FSM:
    def __init__(self, init_state):
        self._state = init_state
        init_state.enter()
        
    def event(self, **kwargs):
        old_state = self._state
        new_state = self._state.next(**kwargs)
        if new_state is None:
            return
        old_state.exit(**kwargs)
        self._state = new_state
        new_state.enter(**kwargs)
        