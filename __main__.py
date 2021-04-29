#!/usr/bin/env python3

import argparse
import sys

from . grbl import *
from . import input
from . fsm import FSM, State

import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# \todo\think Don't normalize axis input feels strange when use of z-axis slows down x and y.
# https://github.com/gnea/grbl/wiki/Grbl-v1.1-jogging#how-to-compute-incremental-distances

    
dt_idle = 0.1

    
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
    
    
class app:
    
    # Main app states #########################################################
    
    class off(State):
        def enter():
            app.dt = dt_idle
            print(f"Press start to play...")

        def next():
           if app.input.home_pressed():
                return app.homing

    class homing(State):
        def enter():
            print("Homing start...")
            app.grbl.home()
            print("Homing done.")
            app.input.rumble()

        def next():
            return app.ready

    class ready(State):
        def enter():
            app.dt = dt_idle

        def next():
            if app.v > 0.0:
                return app.jog

    class jog(State):
        def exit():
            # Immediately stop if we hit zero velocity and go to idle.
            app.grbl.jog_cancel()
            return True

        def next():
            if app.v == 0.0:
                return app.ready

            # We are jogging.
            app.dt = app.grbl.calc_dt(app.v)
            s = app.grbl.calc_s(app.v, app.dt)

            t = time.time()
            if(not grbl.jog(s*app.x, s*app.y, s*app.z, app.v)):
                app.input.rumble()
            app.dt -= time.time() - t
            
    ###########################################################################
            
    class speed:
        """Speed states."""
        _lock_button_released = True
        
        # \todo\think Should this go into input.py?
        def _lock_button_event():
            lock_button_pressed = app.input.speed_lock_pressed()
            lock_button_was_released = app.speed._lock_button_released
            app.speed._lock_button_released = not lock_button_pressed
            # The button must first be released before we can issue a new event.
            return lock_button_was_released and lock_button_pressed 
        
        class locked(State):
            def enter():
                app.speed.locked.av = app.input.speed()
                print(f"Speed locked to {app.speed.locked.av*100:.2f} %")
            
            def exit():
                print("Speed unlocked.")
            
            def next():
                if app.speed._lock_button_event():
                    return app.speed.variable
                
            def speed():
                return app.speed.locked.av
            
        class variable(State):            
            def next():
                if app.speed._lock_button_event():
                    return app.speed.locked
            def speed():
                return app.input.speed()
            
        def value():
            return app.speed.fsm._state.speed()
    
    def main(input, grbl):
        app.input = input
        app.grbl = grbl
        app.fsm = FSM(app.off)
        app.speed.fsm = FSM(app.speed.variable)
        
        try:
            while True:
                app.x, app.y, app.z, app.v = grbl.xyzv_from_ax(*app.input.xyz(), app.speed.value())
                app.fsm.event()
                app.speed.fsm.event()
                if app.dt > 0.0:
                    time.sleep(app.dt)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GRBL Xbox360Input jogger.')
    parser.add_argument('file', nargs='?', default=None, type=str, help='path to serial device e.g. /dev/ttyUSB0')
    args = parser.parse_args()
    
    with Input() as input, GRBL(args.file) as grbl:
        app.main(input, grbl)
