#!/usr/bin/env python

from ibid import Ibid

modules = [{'name': 'modules'}, {'name': 'greet'}, {'name': 'datetime'}, {'name': 'saydo'}, {'name': 'complain', 'priority': 1000}, {'name': 'log', 'logfile' : '/tmp/ibid.log'}]
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}
config = {'name': 'Ibid', 'sources': [local], 'modules': modules}
ibid = Ibid(config)
ibid.run()
