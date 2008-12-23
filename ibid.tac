#!/usr/bin/python

import sys
sys.path.append("./lib/wokkel.egg")
from twisted.application import service, internet
from twisted.internet import ssl
from twisted.manhole.telnet import ShellFactory
import dbus
from traceback import print_exc

import ibid

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
config = {'name': 'Ibid', 'sources': {'local': local, 'atrum': atrum, 'jabber': jabber, 'telnet': telnet, 'clock': timer}, 'processors': processors, 'modules': modules}

ibid.config = config
ibid.reload_reloader()
ibid.reloader.reload_dispatcher()
ibid.reloader.load_processors()
ibid.reloader.load_sources(ibidService)

internet.TCPServer(9876, ShellFactory()).setServiceParent(ibidService)
ibidService.setServiceParent(application)
