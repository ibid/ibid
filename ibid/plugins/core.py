"""Core processors for managing events"""

import re
from time import time
from random import choice

import ibid
from ibid.plugins import Processor, match, handler

class Addressed(Processor):

    priority = -1500
    addressed = False

    def __init__(self, name):
        Processor.__init__(self, name)
        self.patterns = [   re.compile(r'^(%s)([:;.?>!,-]+)*\s+' % '|'.join(ibid.config.plugins[name]['names']), re.I),
                            re.compile(r',\s*(%s)\s*$' % '|'.join(ibid.config.plugins[name]['names']), re.I)
                        ]

    @handler
    def handle(self, event):
        if 'addressed' not in event:
            event.addressed = False
            for pattern in self.patterns:
                matches = pattern.search(event.message)
                if matches:
                    event.addressed = matches.group(1)
                    event.message = pattern.sub('', event.message)
                    return event

class Strip(Processor):

    priority = -1600
    addressed = False
    pattern = re.compile(r'^\s*(.*?)[?!.]*\s*$')

    @handler
    def handle(self, event):
        if 'message_raw' not in event:
            event.message_raw = event.message
        event.message = self.pattern.search(event.message).group(1)

class Ignore(Processor):

    addressed = False

    @handler
    def ignore(self, event):
        for who in ibid.config.plugins[self.name]['ignore']:
            if event.who == who:
                event.processed = True

        return event

class Responses(Processor):

    processed = True
    addressed = False
    priority = 1600

    @handler
    def responses(self, event):
        if 'responses' not in event:
            return

        converted = []
        for response in event.responses:
            if isinstance(response, basestring):
                response = {'reply': response}
            if 'target' not in response:
                response['target'] = event.channel
            if 'source' not in response:
                response['source'] = event.source
            converted.append(response)

        event.responses = converted
        return event

acknowledgements = ('Okay', 'Sure', 'Done', 'Righto')

class Address(Processor):

    processed = True

    @handler
    def address(self, event):
        if event.public:
            addressed = []
            for response in event.responses:
                if isinstance(response, bool):
                    response = choice(acknowledgements)
                if isinstance(response, basestring) and event.public:
                    addressed.append('%s: %s' % (event.who, response))
                else:
                    addressed.append(response)

            event.responses = addressed

class Timestamp(Processor):

    def process(self, event):
        event.time = time()
                
# vi: set et sta sw=4 ts=4:
