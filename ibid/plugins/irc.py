"""Administrative commands for IRC"""

from ibid.plugins import Processor, match

class Actions(Processor):
    """Usage: (join|part|leave) <channel>"""

    @match('^\s*(join|part|leave)\s+(#\S*)\s*$')
    def handler(self, event, action, channel):
        if action == u'leave':
            action = 'part'

        ircaction = (action.lower(), channel)

        event.addresponse({'reply': '%sing %s' % ircaction, 'ircaction': ircaction})
        return event

# vi: set et sta sw=4 ts=4:
