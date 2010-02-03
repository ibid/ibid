#!/usr/bin/env python
# Copyright (c) 2009 Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.
#
# Usage: knab.py <filename> <factoid name> [<factoid name>...]

from sys import argv

import simplejson as json

values = ['<reply> ' + line.strip() for line in open(argv[1]).readlines()]
names = argv[2:]
print json.dumps([[names, values]], indent=1)
