"""Administrative commands for IRC"""

import ibid
from ibid.plugins import Processor, match

class Actions(Processor):
    """Usage: (join|part|leave) <channel>"""

    @match('^\s*(join|part|leave)(?:\s+(\S*))?(?:\s+on\s+(\S+))?\s*$')
    def join(self, event, action, channel, source):
        action = action.lower()
        if not source:
            source = event.source
        if not channel:
            if action == 'join':
                return
            channel = event.channel

        if ibid.config.sources[source]['type'] != 'irc' and ibid.config.sources[source]['type'] != 'jabber':
            event.addresponse(u"%s isn't an IRC or Jabber source" % source)
            return

        if action == 'join':
            ibid.sources[source].join(channel)
            event.addresponse(u"Joining %s" % channel)
        else:
            ibid.sources[source].part(channel)
            event.addresponse(u"Parting %s" % channel)

# vi: set et sta sw=4 ts=4:
