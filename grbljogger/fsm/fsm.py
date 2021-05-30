
import sys

import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

from abc import ABC, abstractmethod


class State(ABC):
    def enter(**kwargs):
        """Will be executed after entering."""
        
    def exit(**kwargs):
        """Will be executed before leaving the state."""
        
    @abstractmethod
    def next(**kwargs):
        """Return the next state for a transition or None to stay in this state."""
        pass
        
        
class FSM:
    def __init__(self, init_state):
        self._state = init_state
        init_state.enter()
        
    def event(self, **kwargs):
        new_state = self._state.next(**kwargs)
        if new_state is not None:
            self._state.exit(**kwargs)
            self._state = new_state
            self._state.enter(**kwargs)
        