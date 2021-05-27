#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import glob

if len(sys.argv) > 0:
    for ts in sys.argv:
        ts = os.path.expanduser(ts)

        filename, file_extension = os.path.splitext(ts)
        if file_extension.lower() != '.ts':
            continue

        print("Repairing {}...".format(ts), end="", flush=True)

        if not os.access(ts, os.R_OK):
            print(" FAIL")
            continue

        with open(ts, "r", encoding="utf8") as f:
            orig = f.read()

        orig = orig.replace('<message>', '<message encoding="UTF-8">')
        orig = orig.replace('é', 'é')
        orig = orig.replace('è', 'è')
        orig = orig.replace('à', 'à')
        orig = orig.replace('', '')
        orig = orig.replace('<translation type="obsolete">', '<translation>')

        with open(ts, "w", encoding="utf8") as f:
            f.write(orig)

        print(" OK", flush=True)