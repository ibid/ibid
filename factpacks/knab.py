#!/usr/bin/env python
# Usage: knab.py <filename> <factoid name> [<factoid name>...]

from sys import argv

import simplejson as json

values = ['<reply> ' + line.strip() for line in open(argv[1]).readlines()]
names = argv[2:]
print json.dumps([[names, values]], indent=1)
