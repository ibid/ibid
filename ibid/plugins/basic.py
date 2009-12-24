from random import choice
import re

import ibid
from ibid.plugins import Processor, match, handler, authorise

help = {}

help['saydo'] = u'Says or does stuff in a channel.'
class SayDo(Processor):
    u"""(say|do) in <channel> [on <source>] <text>"""
    feature = 'saydo'

    permission = u'saydo'

    @match(r'^(say|do)\s+(?:in|to)\s+(\S+)\s+(?:on\s+(\S+)\s+)?(.*)$', 'deaddressed')
    @authorise()
    def saydo(self, event, action, channel, source, what):
        event.addresponse(what, address=False, target=channel, source=source or event.source,
                action=(action.lower() == u"do"))

help['redirect'] = u'Redirects the response to a command to a different channel.'
class RedirectCommand(Processor):
    u"""redirect [to] <channel> [on <source>] <command>"""
    feature = 'redirect'

    priority = -1200
    permission = u'saydo'

    @match(r'^redirect\s+(?:to\s+)?(\S+)\s+(?:on\s+(\S+)\s+)?(.+)$')
    @authorise()
    def redirect(self, event, channel, source, command):
        if source:
            if source.lower() not in ibid.sources:
                event.addresponse(u'No such source: %s', source)
                return
            event.redirect_source = source
        event.redirect_target = channel
        event.message['clean'] = command

class Redirect(Processor):
    feature = 'redirect'

    processed = True
    priority = 940

    @handler
    def redirect(self, event):
        if 'redirect_target' in event:
            responses = []
            for response in event.responses:
                if isinstance(response, basestring):
                    response = {'reply': response, 'target': event.redirect_target}
                    if 'redirect_source' in event:
                        response['source'] = event.redirect_source
                responses.append(response)
            event.responses = responses

help['choose'] = u'Choose one of the given options.'
class Choose(Processor):
    u"""choose <choice> or <choice>..."""
    feature = 'choose'

    choose_re = re.compile(r'(?:\s*,\s*(?:or\s+)?)|(?:\s+or\s+)', re.I)

    @match(r'^(?:choose|choice|pick)\s+(.+)$')
    def choose(self, event, choices):
        event.addresponse(u'I choose %s', choice(self.choose_re.split(choices)))

# vi: set et sta sw=4 ts=4:
