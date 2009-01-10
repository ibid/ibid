#!/usr/bin/env python

from sys import argv, exit
from traceback import print_exc

import ibid
from ibid.config import FileConfig
from ibid.event import Event

if len(argv) != 2:
    print 'Usage: test_plugin.py plugin'
    exit(1)

ibid.config = FileConfig("ibid.ini")
ibid.config.merge(FileConfig("local.ini"))
ibid.reload_reloader()
ibid.reloader.reload_databases()
ibid.reloader.reload_dispatcher()
ibid.reloader.load_processor(argv[1])

while True:
    try:
        event = Event('test_plugin', 'message')
        event.who = event.sender = event.sender_id = event.channel = 'test_plugin'
        event.addressed = True
        event.public = False
        event.message = raw_input('Query: ')
        for processor in ibid.processors:
            processor.process(event)
        for response in event.responses:
            if isinstance(response, dict):
                response = response['reply']
            print 'Response: %s' % response
        print event
    except Exception, e:
        print_exc()

# vi: set et sta sw=4 ts=4:
