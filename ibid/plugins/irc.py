"""Administrative commands for IRC"""

import ibid
from ibid.plugins import Processor, match, authorise

help = {"irc": "Provides commands for joining/parting channels on IRC and Jabber, and changing the bot's nick"}

class Actions(Processor):
    """(join|part|leave) [<channel> [on <source>]]
    change nick to <nick> [on <source>]"""
    feature = 'irc'

    permission = 'sources'

    @match(r'^(join|part|leave)(?:\s+(\S*))?(?:\s+on\s+(\S+))?$')
    @authorise
    def channel(self, event, action, channel, source):
        action = action.lower()

        if not source:
            source = event.source
        if not channel:
            if action == 'join':
                return
            channel = event.channel

        if source.lower() not in ibid.sources:
            event.addresponse(u"I don't have a source called %s" % source.lower())
            return

        source = ibid.sources[source.lower()]

        if not hasattr(source, 'join'):
            event.addresponse(u"%s cannot join/part channels" % (source.name,))
            return

        if action == 'join':
            source.join(channel)
            event.addresponse(u"Joining %s" % channel)
        else:
            source.part(channel)
            event.addresponse(u"Parting %s" % channel)

    @match(r'^change\s+nick\s+to\s+(\S+)(?:\s+on\s+(\S+))?$')
    @authorise
    def change_nick(self, event, nick, source):

        if not source:
            source = event.source

        if source.lower() not in ibid.sources:
            event.addresponse(u"I don't have a source called %s" % source.lower())
            return

        source = ibid.sources[source.lower()]

        if not hasattr(source, 'change_nick'):
            event.addresponse(u"%s cannot change nicks" % source)
        else:
            source.change_nick(nick)
            event.addresponse(u'Changing nick to %s' % nick)

# vi: set et sta sw=4 ts=4:
