"""Some basic processors"""

import random

from ibid.module import Module
from ibid.decorators import *

class Greet(Module):
    """Greets people"""

    @addressedmessage('^\s*(?:hi|hello|hey)\s*$')
    def process(self, event):
        """Usage: (hi|hello|hey)"""
        response = u'Hi %s' % event.who
        event.addresponse(response)
        return event

class SayDo(Module):
    """Says or does things in a channel"""

    @addressed
    @notprocessed
    @match('^\s*(say|do)\s+(\S+)\s+(.*)\s*$')
    def process(self, event, action, where, what):
        """Usage: (say|do) <channel> <text>"""
        if (event.who != u"Vhata"):
            reply = u"No!  You're not the boss of me!"
            if action.lower() == "say":
                event['responses'].append({'target': where, 'reply': u"Ooooh! %s was trying to make me say '%s'!" % (event.who, what)})
            else:
                event['responses'].append({'target': where, 'reply': u"refuses to do '%s' for '%s'" % (what, event.who), 'action': True})
        else:
            if action.lower() == u"say":
                reply = {'target': where, 'reply': what}
            else:
                reply = {'target': where, 'reply': what, 'action': True}

        event.addresponse(reply)
        return event

complaints = (u'Huh?', u'Sorry...', u'?', u'Excuse me?')

class Complain(Module):
    """Responds with a complains. Used to handle unprocessed messages."""

    @addressedmessage()
    def process(self, event):
        reply = complaints[random.randrange(len(complaints))]
        if event.public:
            reply = u'%s: %s' % (event.who, reply)

        event.addresponse(reply)
        return event

# vi: set et sta sw=4 ts=4:
