from random import choice
import re
import logging

import ibid
from ibid.plugins import Processor, match, handler, authorise

help = {}

help['saydo'] = 'Says or does stuff in a channel.'
class SayDo(Processor):
    """(say|do) <channel> <text>"""
    feature = 'saydo'

    permission = u'saydo'

    @match(r'^(say|do)\s+(\S+)\s+(.*)$')
    @authorise
    def saydo(self, event, action, where, what):
        reply = {'target': where, 'reply': what}
        if action.lower() == u"do":
            reply['action'] = True

        event.addresponse(reply)
        return event

help['redirect'] = u'Redirects the response to a command to a different channel.'
class RedirectCommand(Processor):
    """redirect [to] <channel> [on <source>] <command>"""
    feature = 'redirect'

    priority = -1200
    permission = u'saydo'

    @match(r'^redirect\s+(?:to\s+)?(\S+)\s+(?:on\s+(\S+)\s+)?(.+)$')
    @authorise
    def redirect(self, event, channel, source, command):
        event.redirect_target = channel
        if source:
            event.redirect_source = source
        event.message = command

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

choose_re = re.compile(r'(?:\s*,\s*(?:or\s+)?)|(?:\s+or\s+)', re.I)
help['choose'] = 'Choose one of the given options.'
class Choose(Processor):
    """choose <choice> or <choice>..."""
    feature = 'choose'

    @match(r'^(?:choose|choice|pick)\s+(.+)$')
    def choose(self, event, choices):
        event.addresponse(u'I choose %s' % choice(choose_re.split(choices)))

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
            self.log.warning(u"Found a non-unicode string: %s" % object)

# vi: set et sta sw=4 ts=4:
