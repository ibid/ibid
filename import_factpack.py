#!/usr/bin/env python

from sys import argv, exit

import ibid
from ibid.config import FileConfig
from ibid.plugins.factoid import FactoidName, FactoidValue

if len(argv) != 2:
    print 'Usage: import_factpack.py <factpack>'
    exit(1)

ibid.config = FileConfig("ibid.ini")
ibid.config.merge(FileConfig("local.ini"))
ibid.reload_reloader()
ibid.reloader.reload_databases()

locals = {}
execfile(argv[1], {}, locals)

session = ibid.databases.ibid()
max = session.query(FactoidName).order_by(FactoidName.factoid_id.desc()).first()
if max and max.factoid_id:
    next = max.factoid_id + 1
else:
    next = 1

for names, values in locals['facts']:
    for name in names:
        factoid = FactoidName(unicode(name), None, next)
        session.save(factoid)
    for value in values:
        factoid = FactoidValue(unicode(value), None, next)
        session.save(factoid)
    next += 1

session.flush()
session.close()
print "Done"

# vi: set et sta sw=4 ts=4:
