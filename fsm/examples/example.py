
# Run as: python -m fsm.examples.example

from ..fsm import *

class Off(State):
    @classmethod
    def enter(cls):
        print(f"Hello from state {cls.__name__}, enter 42 to play.")

    @classmethod
    def update(cls, input):
        if input == 42:
            return Ready
    
class Ready(State):
    @classmethod
    def enter(cls):
        print(f"We are ready to jog, enter something !=0 to jog.")
        
    @classmethod
    def update(cls, input):
        if input != 0:
            return Jog
    
class Jog(State):
    @classmethod
    def enter(cls):
        print(f"Ok, we are jogging, enter 0 to leave jogging.")
        
    @classmethod
    def update(cls, input):
        if input == 0:
            return Ready
    
    
fsm = FSM(init_state=Off)

while True:
    try:
        number = int(input("Enter Number:"))
    except ValueError:
        number = 0
    fsm.update(number)