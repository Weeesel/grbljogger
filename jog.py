#!/usr/bin/env python3

import argparse
import sys
import time
import serial
import contextlib
from enum import Enum
from xbox360controller import Xbox360Controller


# \todo Error handling, specially error 15 which is soft stop.
# \todo Don't normalize axis input feels strange when use of z-axis slows down x and y.


# https://github.com/gnea/grbl/wiki/Grbl-v1.1-Jogging#how-to-compute-incremental-distances

F_max = 6000 # max feedrate [mm/min]
a_max = 1000 # max. acceleration [mm/s²]
dt_idle = 0.1
axis_threshold = 0.2

v_max = F_max / 60


class Joystick(contextlib.AbstractContextManager):
    def __init__(self):
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

        
class SerialDummy(contextlib.AbstractContextManager):
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        pass
    
    def write(self, data):
        print(data[:-1], end='\r\x1b[1K')
        
    def readline(self):
        return b'ok\r\n'
        
        
class GRBL(contextlib.AbstractContextManager):
    def __init__(self, serial_file=None):
        self._serial = SerialDummy() if serial_file is None else serial.Serial(serial_file,115200)
        print(self._serial.readline())
        print(self._serial.readline())
        self.unlock()

    def __enter__(self):
        self._serial.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._serial.__exit__(exc_type, exc_value, traceback)
    
    @staticmethod
    def xyzv_from_ax(ax,ay,az):
        n = (ax**2+ay**2+az**2)**0.5
        if n > 0.0:
            v = v_max * n if n<1 else v_max
            return ax/n, ay/n, az/n, v
        else:
            return 0.0, 0.0, 0.0, 0.0

    @staticmethod
    def calc_s(v, dt):
        return v*dt

    @staticmethod
    def calc_dt(v):
        dt_min = 10e-3 # time it takes Grbl to parse and plan one jog command.
        N = 15 # Number of Grbl planner blocks.
        return max(dt_min, v**2 / (2*a_max*(N-1)))
    
    def send(self, line, need_ok=True):
        self._serial.write(f"{line}\n".encode())
        ret = self._serial.readline()
        if need_ok and ret != b'ok\r\n':
            raise Exception("Fuck, shit!", line, ret)
    
    def unlock(self):
        self.send('$X', need_ok=False)
        self._serial.readline()
        
    def home(self):
        self.send('$H')
    
    def jog(self, x, y, z, v):
        """
        grbl jog command
        x: mm
        y: mm
        z: mm
        v: mm/s
        """
        F = 60 * v
        self.send(f"$J=G91X{x:.3f}Y{y:.3f}Z{z:.3f}F{F:.3f}")
        
    def jog_cancel(self):
        self.send(chr(0x85))

    
class UI:
    def update(self):
        pass
    
    
def main(serial_file=None):
    class State(Enum):
        idle = 0
        jog = 1

    state = State.idle
    dt = dt_idle
    
    try:
        with Joystick() as joy:
            with GRBL(serial_file) as grbl:
                while True:
                    x, y, z, v = GRBL.xyzv_from_ax(*joy.xyz())

                    if state == State.idle:
                        if v > 0.0:
                            state = State.jog
                            joy.rumble()
                            continue

                    elif state == State.jog:
                        if v == 0.0:
                            # Immediately stop if we hit zero velocity and go to idle.
                            grbl.jog_cancel()
                            state = State.idle
                            dt = dt_idle
                            joy.rumble()
                        else:
                            # We are jogging.
                            dt = GRBL.calc_dt(v)
                            s = GRBL.calc_s(v, dt)

                            t = time.time()
                            grbl.jog(s*x, s*y, s*z, v)
                            dt -= time.time() - t

                    if dt > 0.0:
                        time.sleep(dt)

    except KeyboardInterrupt:
        pass
    
print(f"""Parameters:
  v_max: {v_max:.3f} mm/s
  dt_max: {GRBL.calc_dt(v_max):.3f} s
""")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GRBL Joystick Jogger.')
    parser.add_argument('file', nargs='?', default=None, type=str, help='path to serial device e.g. /dev/ttyUSB0')
    args = parser.parse_args()
    main(args.file)
