from random import choice

from ibid.plugins import Processor, match, handler

help = {}

help['greet'] = 'Greets people when greeted.'
class Greet(Processor):
    feature = 'greet'

    greetings = (u'Hi %s', u'Hey %s', u'Howzit %s')

    @match(r'^\s*(?:hi|hello|hey)\s*$')
    def greet(self, event):
        """Usage: (hi|hello|hey)"""
        event.addresponse({'reply': choice(self.greetings) % event.who})
        return event

help['saydo'] = 'Says or does stuff in a channel.'
class SayDo(Processor):
    """(say|do) <channel> <text>"""
    feature = 'saydo'

    @match(r'^\s*(say|do)\s+(\S+)\s+(.*)\s*$')
    def saydo(self, event, action, where, what):
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

help['complain'] = 'Responds with a complaint. Used to handle unprocessed messages.'
class Complain(Processor):
    feature = 'complain'

    priority = 900
    complaints = (u'Huh?', u'Sorry...', u'?', u'Excuse me?')

    @handler
    def complain(self, event):
        event.addresponse(choice(self.complaints))
        return event

# vi: set et sta sw=4 ts=4:
