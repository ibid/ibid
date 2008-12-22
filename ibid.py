#!/usr/bin/env python

import ibid.core

modules = [{'name': 'addressed.Module', 'names': ['Ibid', 'bot', 'ant']}, {'name': 'irc.Module'}, {'name': 'ignore.Module', 'ignore': ['NickServ']}, {'name': 'modules.Module'}, {'name': 'greet.Greet'}, {'name': 'datetime.Module'}, {'name': 'saydo.Module'}, {'name': 'complain.Module'}, {'name': 'responses.Module'}, {'name': 'log.Module', 'logfile' : '/tmp/ibid.log'}]
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'name': 'atrum', 'type': 'irc', 'server': 'za.atrum.org', 'port': 6667, 'nick': 'Ibid', 'channels': ['#ibid']}
jabber = {'name': 'jabber', 'type': 'jabber', 'server': 'gorven.za.net', 'port': 5223, 'jid': 'ibid@gorven.za.net/source', 'password': 'z1VdLdxgunupGSju'}
config = {'name': 'Ibid', 'sources': [local, jabber], 'modules': modules}
ibid.core.run(config)
