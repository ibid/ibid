#!/bin/sh -e
# Copyright (c) 2009, Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

python -c 'import this' | python -c 'import sys; import simplejson as json; zen=sys.stdin.readlines(); print json.dumps([[["zen", "zen of python", "python zen"],["<reply> " + l.strip() for l in zen[2:]]]], indent=1)'
