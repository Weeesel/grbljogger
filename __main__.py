#!/usr/bin/env python3

import argparse
import sys

from . grbl import *
from . import input
from . fsm import FSM, State

import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# \todo\think Don't normalize axis input feels strange when use of z-axis slows down x and y.
# https://github.com/gnea/grbl/wiki/Grbl-v1.1-Jogging#how-to-compute-incremental-distances

dt_idle = 0.1
axis_threshold = 0.2

    
print(f"""Parameters:
  v_max: {v_max:.3f} mm/s
  dt_max: {GRBL.calc_dt(v_max):.3f} s
""")


# We try to use the controller first.
try:
    Input = input.Xbox360
# \todo Restrict to some exceptions only.
except Exception as e:
    logging.warning(f"{e}. Falling back to Keyboard input.")
    Input = input.Keyboard
    
    
class Off(State):
    @classmethod
    def entered(cls):
        logging.info(f"Press start to play...")
        
    @classmethod
    def exit(cls):
        logging.info("Homing start...")
        App.grbl.home()
        logging.info("Homing done.")
        App.input.rumble()
        return True

    @classmethod
    def event(cls):
       if App.input.home_pressed():
            return Ready
            
class Ready(State):
    @classmethod
    def entered(cls):
        App.dt = dt_idle
        
    @classmethod
    def event(cls):
        if App.v > 0.0:
            return Jog
    
class Jog(State):     
    @classmethod
    def exit(cls):
        # Immediately stop if we hit zero velocity and go to idle.
        App.grbl.jog_cancel()
        return True
        
    @classmethod
    def event(cls):
        if App.v == 0.0:
            return Ready
            
        # We are jogging.
        App.dt = App.grbl.calc_dt(App.v)
        s = App.grbl.calc_s(App.v, App.dt)

        t = time.time()
        if(not grbl.jog(s*App.x, s*App.y, s*App.z, App.v)):
            App.input.rumble()
        App.dt -= time.time() - t
    
    
class App:
    v = 0.0
    x,y,z = 0.0, 0.0, 0.0
    dt = dt_idle
    
    @classmethod
    def main(cls, input, grbl):
        cls.input = input
        cls.grbl = grbl
        cls.fsm = FSM(Off)
        
        try:
            while True:
                cls.x, cls.y, cls.z, cls.v = grbl.xyzv_from_ax(*input.xyz())
                cls.fsm.event()
                if cls.dt > 0.0:
                    time.sleep(cls.dt)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GRBL Xbox360Input Jogger.')
    parser.add_argument('file', nargs='?', default=None, type=str, help='path to serial device e.g. /dev/ttyUSB0')
    args = parser.parse_args()
    
    with Input() as input, GRBL(args.file) as grbl:
        App.main(input, grbl)
