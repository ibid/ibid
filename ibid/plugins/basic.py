"""Some basic processors"""

from random import choice

from ibid.plugins import Processor, match, handler

class Greet(Processor):
    """Greets people"""

    @match('^\s*(?:hi|hello|hey)\s*$')
    def greet(self, event):
        """Usage: (hi|hello|hey)"""
        response = u'Hi %s' % event.who
        event.addresponse({'reply': response})
        return event

class SayDo(Processor):
    """Says or does things in a channel"""

    @match('^\s*(say|do)\s+(\S+)\s+(.*)\s*$')
    def saydo(self, event, action, where, what):
        """Usage: (say|do) <channel> <text>"""
        if (event.who != u"cocooncrash"):
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

class Complain(Processor):
    """Responds with a complaint. Used to handle unprocessed messages."""

    priority = 900

    @handler
    def complain(self, event):
        event.addresponse(choice(complaints))
        return event

# vi: set et sta sw=4 ts=4:
