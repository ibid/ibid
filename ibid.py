#!/usr/bin/env python

import dbus
import ibid.core

modules = {'core.Addressed': {'names': ['Ibid', 'bot', 'ant']}, 'core.Ignore': {'ignore': ['NickServ']}, 'ping': {'type': 'dbus.Proxy', 'bus_name': 'org.ibid.module.Ping', 'object_path': '/org/ibid/module/Ping', 'pattern': '^ping$'}, 'log.Log': {'logfile' : '/tmp/ibid.log'}}
processors = ['core.Addressed', 'irc.Actions', 'core.Ignore', 'admin.ListModules', 'admin.LoadModules', 'basic.Greet', 'info.DateTime', 'basic.SayDo', 'ping', 'basic.Complain', 'core.Responses', 'log.Log']
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'name': 'atrum', 'type': 'irc', 'server': 'za.atrum.org', 'port': 6667, 'nick': 'Ibid', 'channels': ['#ibid']}
jabber = {'name': 'jabber', 'type': 'jabber', 'server': 'gorven.za.net', 'port': 5223, 'jid': 'ibid@gorven.za.net/source', 'password': 'z1VdLdxgunupGSju'}
config = {'name': 'Ibid', 'sources': {'local': local, 'jabber': jabber}, 'processors': processors, 'modules': modules}
ibid.core.run(config)
