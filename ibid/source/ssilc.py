import os
import time
from os.path import join, exists

from twisted.application import internet
from twisted.internet import task
import silc

import ibid
from ibid.event import Event
from ibid.source import IbidSourceFactory
from ibid.config import Option, IntOption, BoolOption

import logging

class SilcBot(silc.SilcClient):

    channels = {}

    def __init__(self, keys, nick, ident, name, factory):
        self.nick = nick
        silc.SilcClient.__init__(self, keys, nick, ident, name)
        self.factory = factory

    def _create_event(self, type, user, channel):
        event = Event(self.factory.name, type)
        event.sender = unicode("%s@%s" % (user.username, user.hostname), 'utf-8', 'replace')
        event.who = unicode(user.nickname, 'utf-8', 'replace')
        event.sender = self._to_hex(user.user_id)
        event.sender_id = self._to_hex(user.fingerprint)
        event.channel = channel and unicode(channel.channel_name, 'utf-8', 'replace') or event.sender
        event.public = True
        event.source = self.factory.name
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

        if event.channel == self.nick.lower():
            event.addressed = True
            event.public = False
            event.channel = event.who
        else:
            event.public = True

        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        message = response['reply'].replace('\n', ' ')
        channel = self.channels[response['target']]
        if 'action' in response and response['action']:
            self.send_channel_message(channel, message.encode('utf-8'))
            self.factory.log.debug(u"Sent action to %s: %s", response['target'], message)
        else:
            self.send_channel_message(channel, message.encode('utf-8'))
            self.factory.log.debug(u"Sent privmsg to %s: %s", response['target'], message)

    def join(self, channel):
        self.command_call('JOIN %s' % channel)

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
            keys = silc.create_key_pair(pub, prv, passphrase='')
        else:
            keys = silc.load_key_pair(pub, prv, passphrase='')
        self.client = SilcBot(keys, self.nick, self.nick, self.name, self)

    def run_one(self):
        self.client.run_one()
    
    def setServiceParent(self, service):
        s = internet.TimerService(0.2, self.run_one)
        if service is None:
            s.startService()
        else:
            s.setServiceParent(service)

# vi: set et sta sw=4 ts=4:
