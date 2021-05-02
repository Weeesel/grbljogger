#!/usr/bin/env python3

import argparse

from . app import *
from . grbl import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GRBL Xbox360Input jogger.')
    parser.add_argument('file', nargs='?', default=None, type=str, help='path to serial device e.g. /dev/ttyUSB0')
    args = parser.parse_args()
    
    with Input() as input, GRBL(args.file) as grbl:
        app.init(input, grbl)
        app.loop()
