#!/usr/bin/env python

import ibid.core

modules = {'core.Addressed': {'names': ['Ibid', 'bot', 'ant']}, 'core.Ignore': {'ignore': ['NickServ']}, 'log.Log': {'logfile' : '/tmp/ibid.log'}}
processors = ['core.Addressed', 'irc.Actions', 'core.Ignore', 'admin.Modules', 'basic.Greet', 'info.DateTime', 'basic.SayDo', 'basic.Complain', 'core.Responses', 'log.Log']
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'name': 'atrum', 'type': 'irc', 'server': 'za.atrum.org', 'port': 6667, 'nick': 'Ibid', 'channels': ['#ibid']}
jabber = {'name': 'jabber', 'type': 'jabber', 'server': 'gorven.za.net', 'port': 5223, 'jid': 'ibid@gorven.za.net/source', 'password': 'z1VdLdxgunupGSju'}
config = {'name': 'Ibid', 'sources': [local, jabber], 'processors': processors, 'modules': modules}
ibid.core.run(config)
