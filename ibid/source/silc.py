# Copyright (c) 2009-2010, Jonathan Hitchcock, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

# This source requires Python >= 2.5:
from __future__ import absolute_import

from os.path import join, exists

from twisted.application import internet
from silc import SilcClient, create_key_pair, load_key_pair

import ibid
from ibid.event import Event
from ibid.source import IbidSourceFactory
from ibid.config import Option, IntOption, ListOption

import logging

class SilcBot(SilcClient):

    def __init__(self, keys, nick, ident, name, factory):
        self.nick = nick
        SilcClient.__init__(self, keys, nick, ident, name)
        self.factory = factory
        self.channels = {}
        self.users = {}

        self.factory.join = self.join
        self.factory.leave = self.leave
        self.factory.send = self.send

    def _create_event(self, type, user, channel):
        event = Event(self.factory.name, type)
        event.sender['connection'] = unicode("%s@%s" % (user.username, user.hostname), 'utf-8', 'replace')
        event.sender['nick'] = unicode(user.nickname, 'utf-8', 'replace')
        event.sender['connection'] = self._to_hex(user.user_id)
        event.sender['id'] = self._to_hex(user.fingerprint)
        if channel:
            event.channel = unicode(channel.channel_name, 'utf-8', 'replace')
        else:
            event.channel = event.sender['connection']
        event.public = True

        self.users[event.sender['connection']] = user
        self.users[event.sender['id']] = user

        return event

    def _state_event(self, user, channel, action, kicker=None, message=None):
        event = self._create_event(u'state', user, channel)
        event.state = action
        if kicker:
            event.kicker = unicode(self._to_hex(kicker.user_id), 'utf-8', 'replace')
            if message: event.message = unicode(message, 'utf-8', 'replace')
            self.factory.log.debug(u"%s has been kicked from %s by %s (%s)", event.sender['id'], event.channel, event.kicker, event.message)
        else:
            self.factory.log.debug(u"%s has %s %s", event.sender['connection'], action, event.channel)
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def _message_event(self, msgtype, user, channel, msg):
        event = self._create_event(msgtype, user, channel)
        event.message = unicode(msg, 'utf-8', 'replace')
        self.factory.log.debug(u"Received %s from %s in %s: %s", msgtype, event.sender['id'], event.channel, event.message)

        if not channel:
            event.addressed = True
            event.public = False
        else:
            event.public = True

        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        message = response['reply']
        flags=0
        if response.get('action', False):
            flags=4

        if response['target'] in self.users:
            target = self.users[response['target']]
            self.send_private_message(target, message, flags=flags)
        elif response['target'] in self.channels:
            target = self.channels[response['target']]
            if response.get('topic', False):
                self.command_call('TOPIC %s %s' % (target, message))
            else:
                self.send_channel_message(target, message, flags=flags)
        else:
            for user in self.users.itervalues():
                if user.nickname == response['target']:
                    self.send_private_message(user, message, flags=flags)
                    return

            self.factory.log.debug(u"Unknown target: %s" % response['target'])
            return

        self.factory.log.debug(u"Sent message to %s: %s", response['target'], message)

    def logging_name(self, identity):
        format_user = lambda user: u'-'.join((user.nickname,
                                              self._to_hex(user.fingerprint)))
        if identity in self.users:
            user = self.users[identity]
            return format_user(user)
        if identity in self.channels:
            return identity
        # Only really used for saydo
        for user in self.users.itervalues():
            if user.nickname == identity:
                return format_user(user)
        self.factory.log.error(u"Unknown identity: %s", identity)
        return identity

    def join(self, channel):
        self.command_call('JOIN %s' % channel)
        return True

    def leave(self, channel):
        if channel not in self.channels:
            return False

        self.command_call('LEAVE %s' % channel)
        del self.channels[channel]

        # TODO: When pysilc gets channel.user_list support
        # we should remove stale users

        return True

    def _to_hex(self, string):
        return u''.join(hex(ord(c)).replace('0x', '').zfill(2) for c in string)

    def channel_message(self, sender, channel, flags, message):
        self._message_event(u'message', sender, channel, message)

    def private_message(self, sender, flags, message):
        self._message_event(u'message', sender, None, message)

    def notify_join(self, user, channel):
        self._state_event(user, channel, u'online')

    def notify_leave(self, user, channel):
        self._state_event(user, channel, u'offline')

    def notify_signoff(self, user, channel):
        self._state_event(user, channel, u'offline')
        del self.users[self._to_hex(user.user_id)]
        del self.users[self._to_hex(user.fingerprint)]

    def notify_nick_change(self, user, old_nick, new_nick):
        event = self._create_event(u'state', user, None)
        event.state = u'offline'
        event.sender['nick'] = unicode(old_nick, 'utf-8', 'replace')
        event.othername = unicode(new_nick, 'utf-8', 'replace')
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

        event = self._create_event(u'state', user, None)
        event.state = u'online'
        event.sender['nick'] = unicode(new_nick, 'utf-8', 'replace')
        event.othername = unicode(old_nick, 'utf-8', 'replace')
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def notify_kicked(self, user, message, kicker, channel):
        self._state_event(user, channel, u'kicked', kicker, message)

    def notify_killed(self, user, message, kicker, channel):
        self._state_event(user, channel, u'killed', kicker, message)
        del self.users[self._to_hex(user.user_id)]
        del self.users[self._to_hex(user.fingerprint)]

    def notify_invite(self, channel, channel_name, inviter):
        event = self._create_event(u'invite', inviter, None)
        event.target_channel = channel
        event.public = False
        event.addressed = True
        self.factory.log.debug(u'Invited into %s by %s',
                                channel_name,
                                event.sender['id'])
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def running(self):
        self.connect_to_server(self.factory.server, self.factory.port)

    def connected(self):
        for channel in self.factory.channels:
            self.join(channel)

        event = Event(self.factory.name, u'source')
        event.status = u'connected'
        ibid.dispatcher.dispatch(event)

    def command_reply_join(self, channel, name, topic, hmac, x, y, users):
        self.channels[name] = channel
        for user in users:
            self._state_event(user, channel, u'online')

    def disconnect(self):
        self.command_call('QUIT')

    def disconnected(self, message):
        self.factory.log.info(u"Disconnected (%s)", message)

        event = Event(self.factory.name, u'source')
        event.status = u'disconnected'
        ibid.dispatcher.dispatch(event)

        self.factory.s.stopService()
        self.channels.clear()
        self.users.clear()

    def failure(self):
        self.factory.log.error(u'Connection failure')

class SourceFactory(IbidSourceFactory):

    auth = ('implicit',)
    supports = ('action', 'topic')

    server = Option('server', 'Server hostname')
    port = IntOption('port', 'Server port number', 706)
    nick = Option('nick', 'Nick', ibid.config['botname'])
    channels = ListOption('channels', 'Channels to autojoin', [])
    realname = Option('realname', 'Real Name', ibid.config['botname'])
    public_key = Option('public_key', 'Filename of public key', 'silc.pub')
    private_key = Option('private_key', 'Filename of private key', 'silc.prv')
    max_public_message_length = IntOption('max_public_message_length',
            'Maximum length of public messages', 512)

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        self.log = logging.getLogger('source.%s' % self.name)
        pub = join(ibid.options['base'], self.public_key)
        prv = join(ibid.options['base'], self.private_key)
        if not exists(pub) and not exists(prv):
            keys = create_key_pair(pub, prv, passphrase='')
        else:
            keys = load_key_pair(pub, prv, passphrase='')
        self.client = SilcBot(keys, self.nick, self.nick, self.realname, self)

    def run_one(self):
        self.client.run_one()

    def setServiceParent(self, service):
        self.s = internet.TimerService(0.2, self.run_one)
        if service is None:
            self.s.startService()
        else:
            self.s.setServiceParent(service)

    def disconnect(self):
        self.client.disconnect()
        return True

    def url(self):
        return u'silc://%s@%s:%s' % (self.nick, self.server, self.port)

    def logging_name(self, identity):
        return self.client.logging_name(identity)

    def truncation_point(self, response, event=None):
        if response.get('target', None) in self.client.channels:
            return self.max_public_message_length
        return None

# vi: set et sta sw=4 ts=4:
