#!/usr/bin/env python3
# vim: noexpandtab ts=2 sw=2 sts=2

import sys, os

from glob import glob

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config

for fn in glob(os.path.join(config.PLOT_DIR, 'clients_*.svg')):
	print(fn)
