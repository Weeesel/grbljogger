#!/usr/bin/env python3

import argparse
import sys
import time
import serial
import contextlib
from enum import Enum
from xbox360controller import Xbox360Controller

import logging
log = logging.getLogger()
#log.setLevel(logging.DEBUG) # \todo
#log.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))


# \todo\think Don't normalize axis input feels strange when use of z-axis slows down x and y.


# https://github.com/gnea/grbl/wiki/Grbl-v1.1-Jogging#how-to-compute-incremental-distances

# \todo Read speed/acceleration settings from grbl.
F_max = 3000 # max feedrate [mm/min]
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
        
    def home_pressed():
        return self._joystick.button_start.is_pressed()
        
        
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
    EOL = b'\r\n'
    error_strs = {
        # https://github.com/gnea/grbl/wiki/Grbl-v1.1-Interface#grbl-response-messages
        1: "G-code words consist of a letter and a value. Letter was not found.",
        2: "Numeric value format is not valid or missing an expected value.",
        3: "Grbl '$' system command was not recognized or supported.",
        4: "Negative value received for an expected positive value.",
        5: "Homing cycle is not enabled via settings.",
        6: "Minimum step pulse time must be greater than 3usec",
        7: "EEPROM read failed. Reset and restored to default values.",
        8: "Grbl '$' command cannot be used unless Grbl is IDLE. Ensures smooth operation during a job.",
        9: "G-code locked out during alarm or jog state",
        10: "Soft limits cannot be enabled without homing also enabled.",
        11: "Max characters per line exceeded. Line was not processed and executed.",
        12: "(Compile Option) Grbl '$' setting value exceeds the maximum step rate supported.",
        13: "Safety door detected as opened and door state initiated.",
        14: "(Grbl-Mega Only) Build info or startup line exceeded EEPROM line length limit.",
        15: "Jog target exceeds machine travel. Command ignored.",
        16: "Jog command with no '=' or contains prohibited g-code.",
        17: "Laser mode requires PWM output.",
        20: "Unsupported or invalid g-code command found in block.",
        21: "More than one g-code command from same modal group found in block.",
        22: "Feed rate has not yet been set or is undefined.",
        23: "G-code command in block requires an integer value.",
        24: "Two G-code commands that both require the use of the XYZ axis words were detected in the block.",
        25: "A G-code word was repeated in the block.",
        26: "A G-code command implicitly or explicitly requires XYZ axis words in the block, but none were detected.",
        27: "N line number value is not within the valid range of 1 - 9,999,999.",
        28: "A G-code command was sent, but is missing some required P or L value words in the line.",
        29: "Grbl supports six work coordinate systems G54-G59. G59.1, G59.2, and G59.3 are not supported.",
        30: "The G53 G-code command requires either a G0 seek or G1 feed motion mode to be active. A different motion was active.",
        31: "There are unused axis words in the block and G80 motion mode cancel is active.",
        32: "A G2 or G3 arc was commanded but there are no XYZ axis words in the selected plane to trace the arc.",
        33: "The motion command has an invalid target. G2, G3, and G38.2 generates this error, if the arc is impossible to generate or if the probe target is the current position.",
        34: "A G2 or G3 arc, traced with the radius definition, had a mathematical error when computing the arc geometry. Try either breaking up the arc into semi-circles or quadrants, or redefine them with the arc offset definition.",
        35: "A G2 or G3 arc, traced with the offset definition, is missing the IJK offset word in the selected plane to trace the arc.",
        36: "There are unused, leftover G-code words that aren't used by any command in the block.",
        37: "The G43.1 dynamic tool length offset command cannot apply an offset to an axis other than its configured axis. The Grbl default axis is the Z-axis.",
        38: "Tool number greater than max supported value.",
    }
    
    def __init__(self, serial_file=None):
        if serial_file is None:
            self._serial = SerialDummy() 
        else:
            self._serial = serial.Serial(port=serial_file, baudrate=115200)
        
        # Clear welcome message.
        time.sleep(1)
        log.info(self._serial.read_all())
        log.info(self.status())

    def __enter__(self):
        self._serial.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._serial.__exit__(exc_type, exc_value, traceback)
    
    def send(self, line):
        self._serial.write(f"{line}{self.EOL}".encode())
    
    # \todo\think read_until
    def read(self, read_until=[b'ok', b'error', b'ALARM', b'<', b'[', b'Grbl']):
        """Read lines until ok or error."""
        lines = []
        while True:
            line = self._serial.readline()[:-len(self.EOL)]
            lines.append(line)
            if any(map(line.startswith, read_until)):
                return lines
    
    def response(self, send, allowed_errors=[]):
        """Send command and read GRBL response Messages."""
        self.send(send)
        lines = self.read()
        if lines[-1].startswith(b'error'):
            error_code = int(lines[-1][len(b'error: '):])
            msg = f"Fuck, Shit! {self.error_strs[error_code]} Error ({error_code}) appeard after {send}."
            if error_code in allowed_errors:
                log.debug(msg)
            else:
                raise Exception(msg)
        return lines
    
    def status(self):
        return(self.response('?'))
    
    def unlock(self):
        self.send('$X')
        self._serial.readline()
        
    def home(self):
        self.send('$H')
            
    
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
    
    def jog(self, x, y, z, v):
        """
        grbl jog command
        x: mm
        y: mm
        z: mm
        v: mm/s
        """
        F = 60 * v
        # \todo Error 8???
        self.response(f"$J=G91X{x:.3f}Y{y:.3f}Z{z:.3f}F{F:.3f}", allowed_errors=[8,15])
        
    def jog_cancel(self):
        self.send(chr(0x85))

    
class UI:
    def update(self):
        pass
    
    
def main(serial_file=None):
    class State(Enum):
        off = 0
        ready = 1
        jog = 2

    state = State.off
    dt = dt_idle
    
    print("Press start to initiate homing cycle...")
    
    try:
        with Joystick() as joy:
            with GRBL(serial_file) as grbl:
                while True:
                    x, y, z, v = GRBL.xyzv_from_ax(*joy.xyz())

                    if state == State.off:
                        if joy.home_pressed():
                            grbl.home()
                            state = State.ready
                        
                    elif state == State.ready:
                        if v > 0.0:
                            state = State.jog
                            continue

                    elif state == State.jog:
                        if v == 0.0:
                            # Immediately stop if we hit zero velocity and go to idle.
                            grbl.jog_cancel()
                            state = State.ready
                            dt = dt_idle
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
