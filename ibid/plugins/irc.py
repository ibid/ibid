"""Administrative commands for IRC"""

import logging

import ibid
from ibid.plugins import Processor, match, handler, authorise

log = logging.getLogger('plugins.irc')

help = {"irc": u"Provides commands for joining/parting channels on IRC and Jabber, and changing the bot's nick"}

class Actions(Processor):
    u"""(join|part|leave) [<channel> [on <source>]]
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

        if source not in ibid.sources:
            event.addresponse(u"I am not connected to %s", source)
            return

        source = ibid.sources[source]

        if not hasattr(source, 'join'):
            event.addresponse(u'%s cannot join/part channels', source.name)
            return

        if action == 'join':
            source.join(channel)
            event.addresponse(u'Joining %s', channel)
        else:
            source.part(channel)
            event.addresponse(u'Parting %s', channel)

    @match(r'^change\s+nick\s+to\s+(\S+)(?:\s+on\s+(\S+))?$')
    @authorise
    def change_nick(self, event, nick, source):

        if not source:
            source = event.source

        if source not in ibid.sources:
            event.addresponse(u"I am not connected to %s", source.lower())
            return

        source = ibid.sources[source]

        if not hasattr(source, 'change_nick'):
            event.addresponse(u'%s cannot change nicks', source)
        else:
            source.change_nick(nick)
            event.addresponse(u'Changing nick to %s', nick)

class NickServ(Processor):
    event_types = ('notice',)

    def is_nickserv(self, event):
        source_cfg = ibid.config['sources'][event.source]
        return (event.sender.get('nick') == u'NickServ' and (
                u'nickserv_connection' not in source_cfg or
                source_cfg[u'nickserv_connection'] == event.sender['connection']
        ))

    @match(r'^(?:This nickname is registered\. Please choose a different nickname'
            r'|This nickname is registered and protected\.  If it is your)')
    def auth(self, event):
        if self.is_nickserv(event):
            source_cfg = ibid.config['sources'][event.source]
            if u'nickserv_password' in source_cfg:
                event.addresponse(u'IDENTIFY %s', source_cfg[u'nickserv_password'])

    @match(r'^(?:You are now identified for'
            r'|Password accepted -+ you are now recognized)')
    def success(self, event):
        if self.is_nickserv(event):
            log.info(u'Authenticated with NickServ')

# vi: set et sta sw=4 ts=4:
