#!/usr/bin/env python

import ibid.core

modules = [{'name': 'addressed.Module', 'names': ['Ibid', 'bot', 'ant']}, {'name': 'irc.Module'}, {'name': 'ignore.Module', 'ignore': ['NickServ']}, {'name': 'modules.Module'}, {'name': 'greet.Module'}, {'name': 'datetime.Module'}, {'name': 'saydo.Module'}, {'name': 'complain.Module'}, {'name': 'responses.Module'}, {'name': 'log.Module', 'logfile' : '/tmp/ibid.log'}]
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'name': 'atrum', 'type': 'irc', 'server': 'za.atrum.org', 'port': 6667, 'nick': 'Ibid', 'channels': ['#ibid']}
config = {'name': 'Ibid', 'sources': [local], 'modules': modules}
ibid.core.run(config)
