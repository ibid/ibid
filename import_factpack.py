#!/usr/bin/env python

from sys import argv, exit

import ibid
from ibid.config import FileConfig
from ibid.plugins.factoid import Factoid, FactoidName, FactoidValue

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

for names, values in locals['facts']:
    factoid = Factoid()
    for name in names:
        fname = FactoidName(unicode(name), None)
        factoid.names.append(fname)
    for value in values:
        fvalue = FactoidValue(unicode(value), None)
        factoid.values.append(fvalue)
    session.save(factoid)

session.flush()
session.close()
print "Done"

# vi: set et sta sw=4 ts=4:
