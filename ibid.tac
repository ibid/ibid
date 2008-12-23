#!/usr/bin/python

import sys
sys.path.append("./lib/wokkel.egg")
from twisted.application import service, internet
from twisted.internet import ssl
from twisted.manhole.telnet import ShellFactory
import dbus
from traceback import print_exc

import ibid
from ibid.config import StaticConfig

application = service.Application("Ibid")
ibidService = service.MultiService()

ibid.config = FileConfig("ibid.ini")
ibid.config.merge("local.ini")
ibid.reload_reloader()
ibid.reloader.reload_dispatcher()
ibid.reloader.load_processors()
ibid.reloader.load_sources(ibidService)

internet.TCPServer(9876, ShellFactory()).setServiceParent(ibidService)
ibidService.setServiceParent(application)
