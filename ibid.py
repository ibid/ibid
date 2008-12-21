#!/usr/bin/env python

from ibid import Ibid

config = {'sources': [{'name': 'atrum', 'type': 'irc', 'server': 'localhost', 'port': 6667, 'nick': 'Ibid', 'channels': ['#cocoontest']}]}
ibid = Ibid(config)
ibid.run()
