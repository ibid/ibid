from random import choice

import ibid
from ibid.plugins import Processor, match, handler, authorise

help = {}

help['greet'] = 'Greets people when greeted.'
class Greet(Processor):
    feature = 'greet'

    greetings = (u'Hi %s', u'Hey %s', u'Howzit %s')

    @match(r'^(?:hi|hello|hey)$')
    def greet(self, event):
        """Usage: (hi|hello|hey)"""
        event.addresponse({'reply': choice(self.greetings) % event.who})
        return event

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
        event.redirect = channel
        if source:
            event.redirect_source = source
        event.message = command

class Redirect(Processor):
    feature = 'redirect'

    processed = True
    priority = 1700

    @handler
    def redirect(self, event):
        if 'redirect' in event:
            for response in event.responses:
                if response['target'] == event.channel:
                    response['target'] = event.redirect
                    if 'redirect_source' in event:
                        response['source'] = event.redirect_source

help['complain'] = 'Responds with a complaint. Used to handle unprocessed messages.'
class Complain(Processor):
    feature = 'complain'

    priority = 950
    complaints = (u'Huh?', u'Sorry...', u'?', u'Excuse me?')

    @handler
    def complain(self, event):
        event.addresponse(choice(self.complaints))
        return event

# vi: set et sta sw=4 ts=4:
