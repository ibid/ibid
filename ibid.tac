#!/usr/bin/python

import sys
sys.path.append("./lib/wokkel.egg")
from twisted.application import service, internet
from twisted.internet import ssl
from twisted.manhole.telnet import ShellFactory
import dbus
import ibid.core
from traceback import print_exc

application = service.Application("Ibid")
ibidService = service.MultiService()

modules = {
	    'core.Addressed': {'names': ['Ibid', 'bot', 'ant']}, 
	    'core.Ignore': {'ignore': ['NickServ']}, 
	    #'ping': {'type': 'dbus.Proxy', 'bus_name': 'org.ibid.module.Ping', 'object_path': '/org/ibid/module/Ping', 'pattern': '^ping$'},
	    'log.Log': {'logfile' : '/tmp/ibid.log'}}
processors = ['core.Addressed', 'irc.Actions', 'core.Ignore', 'admin.ListModules', 'admin.LoadModules', 'basic.Greet', 'info.DateTime', 'basic.SayDo', 'test.Delay', 'basic.Complain', 'core.Responses', 'log.Log']
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'type': 'irc', 'server': 'za.atrum.org', 'nick': 'Ibid', 'channels': ['#ibid']}
jabber = {'type': 'jabber', 'server': 'jabber.org', 'ssl': True, 'jid': 'ibidbot@jabber.org/source', 'password': 'ibiddev'}
myjabber = {'name': 'jabber', 'type': 'jabber', 'server': 'gorven.za.net', 'ssl': True, 'jid': 'ibid@gorven.za.net/source', 'password': 'z1VdLdxgunupGSju'}
telnet = {'type': 'telnet', 'port': 3000}
timer = {'type': 'timer', 'step': 5}
config = {'name': 'Ibid', 'sources': {'atrum': local, 'jabber': myjabber, 'telnet': telnet, 'timer': timer}, 'processors': processors, 'modules': modules}

ibid.core.config = config
ibid.core.reload_reloader()
ibid.core.reloader.reload_dispatcher()
ibid.core.reloader.load_processors()
ibid.core.reloader.load_sources(ibidService)

internet.TCPServer(9876, ShellFactory()).setServiceParent(ibidService)
ibidService.setServiceParent(application)
