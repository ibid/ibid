#!/usr/bin/env python

from ibid import Ibid

modules = {'greet': None, 'datetime': None, 'saydo': None, 'complain': None, 'log': {'logfile' : '/tmp/ibid.log'}}
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}
config = {'name': 'Ibid', 'sources': [local], 'modules': modules}
ibid = Ibid(config)
ibid.run()
