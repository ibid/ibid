"""Core processors for managing events"""

import re
from time import time

import ibid
from ibid.plugins import Processor, match, handler

class Addressed(Processor):

    priority = -1500
    addressed = False

    def __init__(self, name):
        Processor.__init__(self, name)
        self.pattern = re.compile(r'^\s*(%s)([:;.?>!,-]+)*\s+' % '|'.join(ibid.config.plugins[name]['names']), re.I)

    @handler
    def handle(self, event):
        if 'addressed' not in event:
            newmsg = self.pattern.sub('', event.message)
            if newmsg != event.message:
                event.addressed = True
                event.message = newmsg
            else:
                event.addressed = False
        return event

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

class Address(Processor):

    processed = True

    @handler
    def address(self, event):
        if event.public:
            addressed = []
            for response in event.responses:
                if isinstance(response, basestring) and event.public:
                    addressed.append('%s: %s' % (event.who, response))
                else:
                    addressed.append(response)

            event.responses = addressed

class Timestamp(Processor):

    addressed = False
    priority = -1900

    @handler
    def timestamp(self, event):
        event.time = time()
                
# vi: set et sta sw=4 ts=4:
