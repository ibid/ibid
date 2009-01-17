"""Administrative commands for IRC"""

import ibid
from ibid.plugins import Processor, match

class Actions(Processor):
    """Usage: (join|part|leave) <channel>"""

    @match(r'^(join|part|leave)(?:\s+(\S*))?(?:\s+on\s+(\S+))?$')
    def channel(self, event, action, channel, source):
        action = action.lower()

        if not source:
            source = event.source
        source = source.lower()
        if not channel:
            if action == 'join':
                return
            channel = event.channel

        source = ibid.sources[source]

        if ibid.config.sources[source.name]['type'] != 'irc' and ibid.config.sources[source.name]['type'] != 'jabber':
            event.addresponse(u"%s isn't an IRC or Jabber source" % source.name)
            return

        if action == 'join':
            source.join(channel)
            event.addresponse(u"Joining %s" % channel)
        else:
            source.part(channel)
            event.addresponse(u"Parting %s" % channel)

    @match(r'^change\s+nick\s+to\s+(\S+)(?:\s+on\s+(\S+))?$')
    def change_nick(self, event, nick, source):

        if not source:
            source = event.source
        source = ibid.sources[source.lower()]

        if ibid.config.sources[source.name]['type'] != 'irc':
            event.addresponse(u"%s isn't an IRC source" % source)
        else:
            source.change_nick(nick)
            event.addresponse(u'Changing nick to %s' % nick)

# vi: set et sta sw=4 ts=4:
