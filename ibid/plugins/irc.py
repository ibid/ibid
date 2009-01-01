"""Administrative commands for IRC"""

import ibid
from ibid.plugins import Processor, match

class Actions(Processor):
    """Usage: (join|part|leave) <channel>"""

    @match(r'^\s*(join|part|leave)(?:\s+(\S*))?(?:\s+on\s+(\S+))?\s*$')
    def join(self, event, action, channel, source):
        action = action.lower()
        source = source.lower()

        if not source:
            source = event.source
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

# vi: set et sta sw=4 ts=4:
