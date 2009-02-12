import os
import time
from os.path import join, exists

from twisted.application import internet
from twisted.internet import task
from .. silc import SilcClient, create_key_pair, load_key_pair

import ibid
from ibid.event import Event
from ibid.source import IbidSourceFactory
from ibid.config import Option, IntOption, BoolOption

import logging

class SilcBot(SilcClient):

    def __init__(self, keys, nick, ident, name, factory):
        self.nick = nick
        SilcClient.__init__(self, keys, nick, ident, name)
        self.factory = factory
        self.channels = {}
        self.users = {}

    def _create_event(self, type, user, channel):
        event = Event(self.factory.name, type)
        event.sender = unicode("%s@%s" % (user.username, user.hostname), 'utf-8', 'replace')
        event.who = unicode(user.nickname, 'utf-8', 'replace')
        event.sender = self._to_hex(user.user_id)
        event.sender_id = self._to_hex(user.fingerprint)
        event.channel = channel and unicode(channel.channel_name, 'utf-8', 'replace') or event.sender
        event.public = True
        event.source = self.factory.name

        if event.sender not in self.users:
            self.users[event.sender] = user

        return event

    def _state_event(self, user, channel, action, kicker=None, message=None):
        event = self._create_event(u'state', user, channel)
        event.state = action
        if kicker:
            event.kicker = unicode(kicker, 'utf-8', 'replace')
            if message: event.message = unicode(message, 'utf-8', 'replace')
            self.factory.log.debug(u"%s has been kicked from %s by %s (%s)", event.sender_id, event.channel, event.kicker, event.message)
        else:
            self.factory.log.debug(u"%s has %s %s", user, action, channel)
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def _message_event(self, msgtype, user, channel, msg):
        event = self._create_event(msgtype, user, channel)
        event.message = unicode(msg, 'utf-8', 'replace')
        self.factory.log.debug(u"Received %s from %s in %s: %s", msgtype, event.sender_id, event.channel, event.message)

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
        message = response['reply'].replace('\n', ' ').encode('utf-8')

        if response['target'] in self.users:
            target = self.users[response['target']]
            self.send_private_message(target, message, flags='action' in response and response['action'] and 4 or 0)
        elif response['target'] in self.channels:
            target = self.channels[response['target']]
            self.send_channel_message(target, message, flags='action' in response and response['action'] and 4 or 0)
        else:
            self.factory.log.debug(u"Unknown target: %s" % response['target'])
            return

        self.factory.log.debug(u"Sent message to %s: %s", response['target'], message)

    def join(self, channel):
        self.command_call('JOIN %s' % channel)
        return True

    def part(self, channel):
        if channel not in self.channels:
            return False

        self.command_call('LEAVE %s' % channel)
        del self.channels[channel]
        return True

    def _to_hex(self, string):
        return u''.join(hex(ord(c)).replace('0x', '').zfill(2) for c in string)

    def channel_message(self, sender, channel, flags, message):
        self._message_event(u'message', sender, channel, message)

    def private_message(self, sender, flags, message):
        self._message_event(u'message', sender, None, message)

    def running(self):
        self.connect_to_server(self.factory.server)

    def connected(self):
        for channel in self.factory.channels:
            self.join(channel)

    def command_reply_join(self, channel, name, topic, hmac, x, y, users):
        self.channels[name] = channel

class SourceFactory(IbidSourceFactory):

    auth = ('implicit',)
    server = Option('server', 'Server hostname')
    nick = Option('nick', 'Nick', ibid.config['botname'])
    channels = Option('channels', 'Channels to autojoin', [])
    realname = Option('realname', 'Real Name', ibid.config['botname'])
    public_key = Option('public_key', 'Filename of public key', 'silc.pub')
    private_key = Option('private_key', 'Filename of private key', 'silc.prv')

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        self.log = logging.getLogger('source.%s' % self.name)
        pub = join(ibid.options['base'], self.public_key)
        prv = join(ibid.options['base'], self.private_key)
        if not exists(pub) and not exists(prv):
            keys = create_key_pair(pub, prv, passphrase='')
        else:
            keys = load_key_pair(pub, prv, passphrase='')
        self.client = SilcBot(keys, self.nick, self.nick, self.name, self)

    def join(self, channel):
        return self.client.join(channel)

    def part(self, channel):
        return self.client.part(channel)

    def run_one(self):
        self.client.run_one()
    
    def setServiceParent(self, service):
        s = internet.TimerService(0.2, self.run_one)
        if service is None:
            s.startService()
        else:
            s.setServiceParent(service)

# vi: set et sta sw=4 ts=4:
