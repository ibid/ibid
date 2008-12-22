#!/usr/bin/python

from twisted.application import service, internet
from twisted.internet import ssl
from twisted.manhole.telnet import ShellFactory
import dbus
import ibid.core

application = service.Application("Ibid")
ibidService = service.MultiService()

modules = {
            'core.Addressed': {'names': ['Ibid', 'bot', 'ant']}, 
            'core.Ignore': {'ignore': ['NickServ']}, 
            #'ping': {'type': 'dbus.Proxy', 'bus_name': 'org.ibid.module.Ping', 'object_path': '/org/ibid/module/Ping', 'pattern': '^ping$'},
            'log.Log': {'logfile' : '/tmp/ibid.log'}}
processors = ['core.Addressed', 'irc.Actions', 'core.Ignore', 'admin.Modules', 'basic.Greet', 'info.DateTime', 'basic.SayDo', 'basic.Complain', 'core.Responses', 'log.Log']
#local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'name': 'atrum', 'type': 'irc', 'server': 'za.atrum.org', 'port': 6667, 'nick': 'Ibid', 'channels': ['#ibid']}
jabber = {'name': 'jabber', 'type': 'jabber', 'server': 'jabber.org', 'port': 5223, 'jid': 'ibidbot@jabber.org/source', 'password': 'ibiddev'}
config = {'name': 'Ibid', 'sources': [atrum, jabber], 'processors': processors, 'modules': modules}

ibid.core.config = config
ibid.core.reload_reloader()
ibid.core.reloader.reload_dispatcher()
ibid.core.reloader.load_processors()
for source in ibid.core.config['sources']:
    if source['type'] == 'irc':
        ibid.core.sources[source['name']] = ibid.source.irc.SourceFactory(source)
        internet.TCPClient(source['server'], source['port'], ibid.core.sources[source['name']]).setServiceParent(ibidService)
    if source['type'] == 'jabber':
	ibid.core.sources[source['name']] = ibid.source.jabber.SourceFactory(source)
        internet.SSLClient(source['server'], source['port'], ibid.core.sources[source['name']], ssl.ClientContextFactory()).setServiceParent(ibidService)

internet.TCPServer(9876, ShellFactory()).setServiceParent(ibidService)
ibidService.setServiceParent(application)

