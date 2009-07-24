#!/bin/sh -e
python -c 'import this' | python -c 'import sys; import simplejson as json; zen=sys.stdin.readlines(); print json.dumps([[["zen"],["<reply> " + l.strip() for l in zen[2:]]]], indent=1)'
