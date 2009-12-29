#!/usr/bin/env python

import re
from collections import defaultdict
from sys import argv

try:
    import json
except ImportError:
    import simplejson as json

def default():
    return ([], [])
factoids = defaultdict(default)

for line in open(argv[1]):
    line = line.strip()

    match = re.match(r'^verb (.+) (\d+)$', line)
    if match:
        name, id = match.groups()
        factoids[int(id)][0].append(name)
        continue

    match = re.match(r'^(\d+) (action|reply) (.+)$', line)
    if match:
        id, action, value = match.groups()
        factoids[int(id)][1].append('<%s> %s' % (action, value.replace('##', '$1')))

for names, values in factoids.values():
    for value in values:
        if '$1' in value:
            for index, name in enumerate(names):
                names[index] = name + ' $arg'
            break

print json.dumps(factoids.values(), indent=1)
