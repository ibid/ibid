# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

"""Administrative commands for sources"""

from fnmatch import fnmatch
import logging

import ibid
from ibid.plugins import Processor, match, authorise, handler

log = logging.getLogger('plugins.sources')

features = {}

features['actions'] = {
    'description': u"Provides commands for joining/parting channels on IRC and "
                   u"Jabber, and changing the bot's nick",
    'categories': ('admin',),
}

class Actions(Processor):
    usage = u"""(join|part|leave) [<channel> [on <source>]]
    change nick to <nick> [on <source>]"""
    features = ('actions',)

    permission = 'sources'

    @match(r'^(join|part|leave)(?:\s+(\S*))?(?:\s+on\s+(\S+))?(?:\s+(?:key\s+)?(\S+))?$')
    @authorise()
    def channel(self, event, action, channel, source, key):
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
            if key:
                if not hasattr(source, 'join_with_key'):
                    event.addresponse(u'%s cannot join key-protected channels',
                            source.name)
                    return
                source.join_with_key(channel, key)
            else:
                source.join(channel)
            event.addresponse(u'Joining %s', channel)
        else:
            source.leave(channel)
            event.addresponse(u'Leaving %s', channel)

    @match(r'^change\s+nick\s+to\s+(\S+)(?:\s+on\s+(\S+))?$')
    @authorise()
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

class Invited(Processor):
    features = ('actions',)

    event_types = ('invite',)
    permission = 'sources'

    @handler
    @authorise()
    def invited(self, event):
        event.addresponse(u'Joining %s', event.channel,
                            target=event.sender['nick'])
        ibid.sources[event.source].join(event.channel)

class NickServ(Processor):
    event_types = (u'notice',)

    def is_nickserv(self, event):
        source_cfg = ibid.config['sources'][event.source]
        return (ibid.sources[event.source].type == 'irc' and
                event.sender.get('nick') ==
                    source_cfg.get(u'nickserv_nick', u'NickServ') and
                fnmatch(event.sender['connection'].split('!', 1)[1],
                    source_cfg.get(u'nickserv_mask', '*')
        ))

    @match(r'^(?:This nickname is registered\. Please choose a different nickname'
            r'|This nickname is registered and protected\.\s+If it is your'
            r'|If this is your nickname, type \/msg NS)', simple=False)
    def auth(self, event):
        if self.is_nickserv(event):
            source_cfg = ibid.config['sources'][event.source]
            if u'nickserv_password' in source_cfg:
                event.addresponse(u'IDENTIFY %s', source_cfg[u'nickserv_password'])

    @match(r'^(?:You are now identified for'
            r'|Password accepted -+ you are now recognized)', simple=False)
    def success(self, event):
        if self.is_nickserv(event):
            log.info(u'Authenticated with NickServ')

features['saydo'] = {
    'description': u'Says or does stuff in a channel.',
    'categories': ('admin', 'fun',),
}
class SayDo(Processor):
    usage = u'(say|do) in <channel> [on <source>] <text>'
    features = ('saydo',)

    permission = u'saydo'

    @match(r'^(say|do)\s+(?:in|to)\s+(\S+)\s+(?:on\s+(\S+)\s+)?(.*)$', 'deaddressed')
    @authorise()
    def saydo(self, event, action, channel, source, what):
        event.addresponse(what, address=False, target=channel, source=source or event.source,
                action=(action.lower() == u"do"))

features['redirect'] = {
    'description': u'Redirects the response to a command to a different '
                   u'channel.',
    'categories': ('admin', 'fun',),
}
class RedirectCommand(Processor):
    usage = u'redirect [to] <channel> [on <source>] <command>'
    features = ('redirect',)

    priority = -1200
    permission = u'saydo'

    @match(r'^redirect\s+(?:to\s+)?(\S+)\s+(?:on\s+(\S+)\s+)?(.+)$')
    @authorise()
    def redirect(self, event, channel, source, command):
        if source:
            if source.lower() not in ibid.sources:
                event.addresponse(u'No such source: %s', source)
                return
            event.redirect_source = source
        event.redirect_target = channel
        event.message['clean'] = command

class Redirect(Processor):
    features = ('redirect',)

    processed = True
    priority = 940

    @handler
    def redirect(self, event):
        if 'redirect_target' in event:
            responses = []
            for response in event.responses:
                response['target'] = event.redirect_target
                if 'redirect_source' in event:
                    response['source'] = event.redirect_source
                responses.append(response)
            event.responses = responses


# vi: set et sta sw=4 ts=4:
