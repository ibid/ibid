#!/usr/bin/env python

import sys
sys.path.append("./lib/wokkel.egg")
sys.path.insert(0, './lib')

from twisted.internet import reactor
import ibid

ibid.setup()
reactor.run()

# vi: set et sta sw=4 ts=4:
