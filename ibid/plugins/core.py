import re
from datetime import datetime, timedelta
from random import choice
import logging

import ibid
from ibid.compat import any
from ibid.config import IntOption, ListOption, DictOption
from ibid.plugins import Processor, handler

class Addressed(Processor):

    priority = -1500
    addressed = False

    names = ListOption('names', 'Names to respond to', [ibid.config['botname']])
    verbs = ListOption('verbs', u'Verbs to ignore', ('is', 'has', 'was', 'might', 'may', 'would', 'will', "isn't", "hasn't", "wasn't", "wouldn't", "won't", 'can', "can't", 'did', "didn't", 'said', 'says', 'should', "shouldn't", 'does', "doesn't"))

    def setup(self):
        self.patterns = [   re.compile(r'^(%s)([:;.?>!,-]+)*\s+' % '|'.join(self.names), re.I | re.DOTALL),
                            re.compile(r',\s*(%s)\s*$' % '|'.join(self.names), re.I | re.DOTALL)
                        ]

    @handler
    def handle_addressed(self, event):
        if 'addressed' not in event:
            event.addressed = False

        for pattern in self.patterns:
            matches = pattern.search(event.message['stripped'])
            if matches:
                new_message = pattern.sub('', event.message['stripped'])
                if (len(matches.groups()) > 1 and not matches.group(2) and
                        any(new_message.lower().startswith(verb)
                            for verb in self.verbs)):
                    return

                event.addressed = matches.group(1)
                event.message['clean'] = new_message
                event.message['deaddressed'] = pattern.sub('', event.message['raw'])

class Strip(Processor):

    priority = -1600
    addressed = False
    event_types = ('message', 'action', 'notice')

    pattern = re.compile(r'^\s*(.*?)\s*[?!.]*\s*$', re.DOTALL)

    @handler
    def handle_strip(self, event):
        if isinstance(event.message, basestring):
            event.message = {'raw': event.message, 'deaddressed': event.message,}
            event.message['clean'] = event.message['stripped'] \
                    = self.pattern.search(event.message['raw']).group(1)

class Ignore(Processor):

    priority = -1500
    addressed = False
    event_types = ('message', 'action', 'notice')

    nicks = ListOption('ignore', 'List of nicks to ignore', [])

    @handler
    def handle_ignore(self, event):
        for who in self.nicks:
            if event.sender['nick'] == who:
                event.processed = True

class IgnorePublic(Processor):

    priority = -1490

    @handler
    def ignore_public(self, event):
        if event.public and not ibid.auth.authorise(event, u'publicresponse'):
            event.addresponse(
                u"Sorry, I'm not allowed to talk to you in public. "
                'Ask me by private message.'
            )

class Address(Processor):

    priority = 1600
    processed = True
    addressed = False

    event_types = ('message', 'action', 'notice', 'state')

    acknowledgements = ListOption('acknowledgements', 'Responses for positive acknowledgements',
            (u'Okay', u'Sure', u'Done', u'Righto', u'Alrighty', u'Yessir'))
    refusals = ListOption('refusals', 'Responses for negative acknowledgements',
            (u'No', u"I won't", u"Shan't", u"I'm sorry, but I can't do that"))

    @handler
    def address(self, event):
        for response in event.responses:
            if isinstance(response['reply'], bool):
                if response:
                    response['reply'] = choice(self.acknowledgements)
                else:
                    response['reply'] = choice(self.refusals)
            if (response.get('address', False)
                    and not response.get('action', False)
                    and not response.get('notice', False)
                    and event.public):
                response['reply'] = ('%s: %s' % (
                    event.sender['nick'], response['reply']))

class Timestamp(Processor):

    priority = -1900

    def process(self, event):
        event.time = datetime.utcnow()

class Complain(Processor):

    priority = 950
    processed = True
    event_types = ('message', 'action')

    complaints = DictOption('complaints', 'Complaint responses', {
        'nonsense': (
            u'Huh?', u'Sorry...',
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
        if 'complain' in event and not event.responses:
            event.addresponse(choice(self.complaints[event.complain]))
        elif event.processed:
            return
        else:
            event.addresponse(choice(self.complaints['nonsense']))

class RateLimit(Processor):

    priority = -1000
    event_types = ('message', 'action', 'notice')

    limit_time = IntOption('limit_time', 'Time period over which to measure messages', 10)
    limit_messages = IntOption('limit_messages', 'Number of messages to allow during the time period', 5)
    messages = {}

    @handler
    def ratelimit(self, event):
        if event.identity not in self.messages:
            self.messages[event.identity] = [event.time]
        else:
            self.messages[event.identity].append(event.time)
            self.messages[event.identity] = filter(
                lambda x: event.time - x < timedelta(seconds=self.limit_time),
                self.messages[event.identity])
            if len(self.messages[event.identity]) > self.limit_messages:
                if event.public:
                    event.addresponse(u'Geez, give me some time to think!', address=False)
                else:
                    event.processed = True

class Format(Processor):
    priority = 2000

    def process(self, event):
        filtered = []
        for response in event.responses:
            source = response['source'].lower()
            supports = ibid.sources[source].supports

            if response.get('action', False) and 'action' not in supports:
                response['reply'] = u'*%s*' % response['reply']

            if (not response.get('conflate', True)
                    and 'multiline' not in supports):
                for line in response['reply'].split('\n'):
                    r = {'reply': line}
                    for k in response.iterkeys():
                        if k not in ('reply', 'conflate'):
                            r[k] = response[k]
                    filtered.append(r)
            else:
                filtered.append(response)

        event.responses = filtered

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
