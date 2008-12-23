#!/usr/bin/env python

import sys
sys.path.append("./lib/wokkel.egg")
import dbus

from twisted.internet import reactor
import ibid
from ibid.config import StaticConfig

ibid.config = FileConfig(argv[1])
ibid.reload_reloader()
ibid.reloader.reload_dispatcher()
ibid.reloader.load_processors()
ibid.reloader.load_sources()
reactor.run()
