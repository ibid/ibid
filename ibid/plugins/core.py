import re
from time import time
from random import choice
import logging

import ibid
from ibid.plugins import Processor, handler
from ibid.config import Option, IntOption

class Addressed(Processor):

    priority = -1500
    addressed = False
    names = Option('names', 'Names to respond to', [ibid.config['botname']])
    verbs = Option('verbs', u'Verbs to ignore', ('is', 'has', 'was', 'might', 'may', 'would', 'will', "isn't", "hasn't", "wasn't", "wouldn't", "won't", 'can', "can't", 'did', "didn't", 'said', 'says', 'should', "shouldn't", 'does', "doesn't"))

    def setup(self):
        self.patterns = [   re.compile(r'^(%s)([:;.?>!,-]+)*\s+' % '|'.join(self.names), re.I),
                            re.compile(r',\s*(%s)\s*$' % '|'.join(self.names), re.I)
                        ]

    @handler
    def handle_addressed(self, event):
        if 'addressed' not in event:
            event.addressed = False

        for pattern in self.patterns:
            matches = pattern.search(event.message)
            if matches:
                new_message = pattern.sub('', event.message)
                if len(matches.groups()) > 1 and not matches.group(2) and new_message.lower().startswith(self.verbs):
                    return

                event.addressed = matches.group(1)
                event.message = new_message

class Strip(Processor):

    priority = -1600
    addressed = False
    pattern = re.compile(r'^\s*(.*?)[?!.]*\s*$')

    @handler
    def handle_strip(self, event):
        if 'message_raw' not in event:
            event.message_raw = event.message
        event.message = self.pattern.search(event.message).group(1)

class Ignore(Processor):

    addressed = False
    priority = -1500

    @handler
    def handle_ignore(self, event):
        for who in ibid.config.plugins[self.name]['ignore']:
            if event.sender['nick'] == who:
                event.processed = True

class Responses(Processor):

    priority = 1600

    def process(self, event):
        if 'responses' not in event:
            event.responses = []
            return

        converted = []
        for response in event.responses:
            if isinstance(response, basestring):
                response = {'reply': response}
            if 'target' not in response:
                response['target'] = event.channel
            if 'source' not in response:
                response['source'] = event.source
            if 'action' in response and (response['source'].lower() not in ibid.sources \
                    or ibid.sources[response['source'].lower()].type not in ('irc', 'silc')):
                response['reply'] = '* %s %s' % (ibid.config['botname'], response['reply'])
            converted.append(response)

        event.responses = converted

class Address(Processor):

    processed = True
    acknowledgements = Option('acknowledgements', 'Responses for positive acknowledgements',
            (u'Okay', u'Sure', u'Done', u'Righto', u'Alrighty', u'Yessir'))
    refusals = Option('refusals', 'Responses for negative acknowledgements',
            (u'No', u"I won't", u"Shan't", u"I'm sorry, but I can't do that"))

    @handler
    def address(self, event):
        addressed = []
        for response in event.responses:
            if isinstance(response, bool):
                if response:
                    response = choice(self.acknowledgements)
                else:
                    response = choice(self.refusals)
            if isinstance(response, basestring) and event.public:
                addressed.append('%s: %s' % (event.sender['nick'], response))
            else:
                addressed.append(response)

        event.responses = addressed

class Timestamp(Processor):

    priority = -1900

    def process(self, event):
        event.time = time()

class Complain(Processor):

    priority = 950
    complaints = Option('complaints', 'Complaint responses', {
        'nonsense': (
            u'Huh?', u'Sorry...', u'?',
            u'Excuse me?', u'*blink*', u'What?',
        ),
        'notauthed': (
            u"I'm not your bitch", u"Just do it yourself",
            u"I'm not going to listen to you", u"You're not the boss of me",
        ),
        'exception': (
            u"I'm not feeling too well", u"That didn't go down very well. Burp.",
            u"That didn't seem to agree with me",
        ),
    })

    @handler
    def complain(self, event):
        if 'complain' in event:
            event.addresponse(u'%s', choice(self.complaints[event.complain]))
        else:
            event.addresponse(u'%s', choice(self.complaints['nonsense']))

class RateLimit(Processor):

    priority = -1000
    limit_time = IntOption('limit_time', 'Time period over which to measure messages', 10)
    limit_messages = IntOption('limit_messages', 'Number of messages to allow during the time period', 5)
    messages = {}

    @handler
    def ratelimit(self, event):
        if event.identity not in self.messages:
            self.messages[event.identity] = [event.time]
        else:
            self.messages[event.identity].append(event.time)
            self.messages[event.identity] = filter(lambda x: event.time-x < self.limit_time, self.messages[event.identity])
            if len(self.messages[event.identity]) > self.limit_messages:
                if event.public:
                    event.addresponse({'reply': u'Geez, give me some time to think!'})
                else:
                    event.processed = True

class UnicodeWarning(Processor):
    priority = 1950

    def setup(self):
        self.log = logging.getLogger('plugins.unicode')

    def process(self, object):
        if isinstance(object, dict):
            for value in object.values():
                self.process(value)
        elif isinstance(object, list):
            for value in object:
                self.process(value)
        elif isinstance(object, str):
            self.log.warning(u'Found a non-unicode string: %s' % object)

# vi: set et sta sw=4 ts=4:
