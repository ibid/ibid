from random import choice
import re

import ibid
from ibid.plugins import Processor, match, handler, authorise

help = {}

help['saydo'] = 'Says or does stuff in a channel.'
class SayDo(Processor):
    """(say|do) <channel> <text>"""
    feature = 'saydo'

    @match(r'^(say|do)\s+(\S+)\s+(.*)$')
    def saydo(self, event, action, where, what):
        if ibid.auth.authenticate(event) and ibid.auth.authorise(event, 'saydo'):
            if action.lower() == u"say":
                reply = {'target': where, 'reply': what}
            else:
                reply = {'target': where, 'reply': what, 'action': True}
        else:
            reply = u"No!  You're not the boss of me!"
            if action.lower() == "say":
                event['responses'].append({'target': where, 'reply': u"Ooooh! %s was trying to make me say '%s'!" % (event.who, what)})
            else:
                event['responses'].append({'target': where, 'reply': u"refuses to do '%s' for '%s'" % (what, event.who), 'action': True})

        event.addresponse(reply)
        return event

help['redirect'] = u'Redirects the response to a command to a different channel.'
class RedirectCommand(Processor):
    """redirect [to] <channel> [on <source>] <command>"""
    feature = 'redirect'

    priority = -1200

    @match(r'^redirect\s+(?:to\s+)?(\S+)\s+(?:on\s+(\S+)\s+)?(.+)$')
    @authorise(u'saydo')
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
        event.addresponse('I choose %s' % choice(choose_re.split(choices)))

# vi: set et sta sw=4 ts=4:
