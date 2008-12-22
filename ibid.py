#!/usr/bin/env python

import ibid.core

modules = [{'name': 'addressed', 'names': ['Ibid', 'bot', 'ant']}, {'name': 'irc'}, {'name': 'ignore', 'ignore': ['NickServ']}, {'name': 'modules'}, {'name': 'greet'}, {'name': 'datetime'}, {'name': 'saydo'}, {'name': 'complain'}, {'name': 'responses'}, {'name': 'log', 'logfile' : '/tmp/ibid.log'}]
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'name': 'atrum', 'type': 'irc', 'server': 'za.atrum.org', 'port': 6667, 'nick': 'Ibid', 'channels': ['#ibid']}
config = {'name': 'Ibid', 'sources': [local], 'modules': modules}
ibid.core.run(config)
