#!/usr/bin/env python

from sys import argv, exit
from traceback import print_exc
import logging

if len(argv) != 2:
    print 'Usage: test_plugin.py plugin'
    exit(1)

import ibid
import ibid.plugins
from ibid.config import FileConfig
from ibid.event import Event

def auth_responses(event, permission):
    return True

ibid.plugins.auth_responses = auth_responses

logging.basicConfig(level=logging.DEBUG)
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
        event.account = event.identity = None
        event.addressed = True
        event.public = False
        event.message = unicode(raw_input('Query: '))
        for processor in ibid.processors:
            processor.process(event)
        for response in event.responses:
            if isinstance(response, dict):
                response = response['reply']
            print 'Response: %s' % response
#        print event
    except Exception, e:
        print_exc()

# vi: set et sta sw=4 ts=4:
