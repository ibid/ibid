#!/usr/bin/env python

from ibid import Ibid

modules = [{'name': 'addressed', 'names': ['Ibid', 'bot', 'ant']}, {'name': 'ignore', 'ignore': ['NickServ']}, {'name': 'modules'}, {'name': 'greet'}, {'name': 'datetime'}, {'name': 'saydo'}, {'name': 'complain'}, {'name': 'responses'}, {'name': 'log', 'logfile' : '/tmp/ibid.log'}]
local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}
atrum = {'name': 'atrum', 'type': 'irc', 'server': 'za.atrum.org', 'port': 6667, 'nick': 'Ibid', 'channels': ['#']}
config = {'name': 'Ibid', 'sources': [atrum], 'modules': modules}
ibid = Ibid(config)
ibid.run()
