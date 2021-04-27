
import contextlib
import time
import logging

from . import serial


# \todo Read speed/acceleration settings from grbl.
F_max = 3000 # max feedrate [mm/min]
a_max = 1000 # max. acceleration [mm/s²]

v_max = F_max / 60


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
            self._serial = serial.Dummy() 
        else:
            self._serial = serial.Serial(port=serial_file, baudrate=115200)
        
        # Clear welcome message.
        logging.debug(self._serial.readline())
        logging.debug(self._serial.readline())
        time.sleep(1)
        logging.debug(self._serial.read_all())
        logging.info(self.status())

    def __enter__(self):
        self._serial.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._serial.__exit__(exc_type, exc_value, traceback)
    
    def send(self, line):
        self._serial.write(f"{line}\n".encode())
    
    # \todo\think read_until
    def read(self, read_until=[b'ok', b'error', b'ALARM']): #, b'<', b'[', b'Grbl']):
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
            error_code = int(lines[-1][len(b'error:'):])
            msg = f"Fuck, Shit! {self.error_strs[error_code]} Error ({error_code}) appeard after {send}."
            if error_code in allowed_errors:
                logging.debug(msg)
            else:
                raise Exception(msg)
        return lines
    
    def status(self):
        return(self.response('?'))
    
    def unlock(self):
        self.send('$X')
        self._serial.readline()
        
    def home(self):
        self.response('$H')
            
    
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
        ret = self.response(f"$J=G91X{x:.3f}Y{y:.3f}Z{z:.3f}F{F:.3f}", allowed_errors=[8,15])
        return ret[-1].startswith(b'ok')
        
    def jog_cancel(self):
        self.response(chr(0x85))