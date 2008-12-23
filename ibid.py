#!/usr/bin/env python

import sys
sys.path.append("./lib/wokkel.egg")
import dbus
import ibid.core

modules = {'core.Addressed': {'names': ['Ibid', 'bot', 'ant']}, 'core.Ignore': {'ignore': ['NickServ']}, 'ping': {'type': 'dbus.Proxy', 'bus_name': 'org.ibid.module.Ping', 'object_path': '/org/ibid/module/Ping', 'pattern': '^ping$'}, 'log.Log': {'logfile' : '/tmp/ibid.log'}}
processors = ['core.Addressed', 'irc.Actions', 'core.Ignore', 'admin.ListModules', 'admin.LoadModules', 'basic.Greet', 'info.DateTime', 'basic.SayDo', 'ping', 'basic.Complain', 'core.Responses', 'log.Log']
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'type': 'irc', 'server': 'za.atrum.org', 'nick': 'Ibid', 'channels': ['#ibid']}
jabber = {'type': 'jabber', 'server': 'jabber.org', 'ssl': True, 'jid': 'ibidbot@jabber.org/source', 'password': 'ibiddev'}
myjabber = {'name': 'jabber', 'type': 'jabber', 'server': 'gorven.za.net', 'ssl': True, 'jid': 'ibid@gorven.za.net/source', 'password': 'z1VdLdxgunupGSju'}
telnet = {'type': 'telnet', 'port': 3000}
timer = {'type': 'timer', 'step': 5}
config = {'name': 'Ibid', 'sources': {'atrum': atrum, 'local': local, 'jabber': jabber, 'myjabber': myjabber, 'telnet': telnet, 'timer': timer}, 'processors': processors, 'modules': modules}
ibid.core.run(config)
