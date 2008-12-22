#!/usr/bin/env python

import ibid.core

modules = [{'name': 'core.Addressed', 'names': ['Ibid', 'bot', 'ant']}, {'name': 'irc.Actions'}, {'name': 'core.Ignore', 'ignore': ['NickServ']}, {'name': 'admin.Modules'}, {'name': 'basic.Greet'}, {'name': 'info.DateTime'}, {'name': 'basic.SayDo'}, {'name': 'basic.Complain'}, {'name': 'core.Responses'}, {'name': 'log.Log', 'logfile' : '/tmp/ibid.log'}]
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'name': 'atrum', 'type': 'irc', 'server': 'za.atrum.org', 'port': 6667, 'nick': 'Ibid', 'channels': ['#ibid']}
jabber = {'name': 'jabber', 'type': 'jabber', 'server': 'gorven.za.net', 'port': 5223, 'jid': 'ibid@gorven.za.net/source', 'password': 'z1VdLdxgunupGSju'}
config = {'name': 'Ibid', 'sources': [local, jabber], 'modules': modules}
ibid.core.run(config)
