#!/usr/bin/python

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
processors = ['core.Addressed', 'irc.Actions', 'core.Ignore', 'admin.ListModules', 'admin.LoadModules', 'basic.Greet', 'info.DateTime', 'basic.SayDo', 'basic.Complain', 'core.Responses', 'log.Log']
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'type': 'irc', 'server': 'za.atrum.org', 'nick': 'Ibid', 'channels': ['#ibid']}
jabber = {'type': 'jabber', 'server': 'jabber.org', 'ssl': True, 'jid': 'ibidbot@jabber.org/source', 'password': 'ibiddev'}
myjabber = {'name': 'jabber', 'type': 'jabber', 'server': 'gorven.za.net', 'ssl': True, 'jid': 'ibid@gorven.za.net/source', 'password': 'z1VdLdxgunupGSju'}
config = {'name': 'Ibid', 'sources': {'local': local, 'jabber': myjabber}, 'processors': processors, 'modules': modules}

ibid.core.config = config
ibid.core.reload_reloader()
ibid.core.reloader.reload_dispatcher()
ibid.core.reloader.load_processors()

for name, config in ibid.core.config['sources'].items():
	module = 'ibid.source.%s' % config['type']
	factory = 'ibid.source.%s.SourceFactory' % config['type']
	try:
		__import__(module)
	except:
		print_exc()

	moduleclass = eval(factory)

	ibid.core.sources[name] = moduleclass(name)
 	(hostname, port, sslctx) = ibid.core.sources[name].paramaters()

	if sslctx:
		internet.SSLClient(hostname, port, ibid.core.sources[name], sslctx).setServiceParent(ibidService)
	else:
		internet.TCPClient(hostname, port, ibid.core.sources[name]).setServiceParent(ibidService)

internet.TCPServer(9876, ShellFactory()).setServiceParent(ibidService)
ibidService.setServiceParent(application)

