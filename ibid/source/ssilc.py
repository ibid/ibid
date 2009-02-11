import silc

import os
import time

from twisted.application import internet
from twisted.internet import task

import ibid
from ibid.event import Event
from ibid.source import IbidSourceFactory

import logging

class SilcBot(silc.SilcClient):
    def _create_event(self, type, user, channel):
        nick = user.split('!', 1)[0]
        event = Event(self.factory.name, type)
        event.sender = unicode(user, 'utf-8', 'replace')
        event.sender_id = unicode(nick, 'utf-8', 'replace')
        event.who = event.sender_id
        event.channel = unicode(channel, 'utf-8', 'replace')
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

        if channel.lower() == self.nickname.lower():
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
        message = response['reply'].replace('\n', ' ')[:490]
        if 'action' in response and response['action']:
            self.send_channel_message(response['target'].encode('utf-8'), message.encode('utf-8'))
            self.factory.log.debug(u"Sent action to %s: %s", response['target'], message)
        else:
            self.send_channel_message(response['target'].encode('utf-8'), message.encode('utf-8'))
            self.factory.log.debug(u"Sent privmsg to %s: %s", response['target'], message)

    # catch responses to commands

    def channel_message(self, sender, channel, flags, message):
        print message
        self._message_event(u'message', sender, channel, message)

    def private_message(self, sender, flags, message):
        print message
        self._message_event(u'message', sender, sender, message)

    def running(self):
        print "* Running"
        self.connect_to_server("reaper.org")

    def connected(self):
        print "* Connected"
        self.command_call("JOIN ibid")

    def command_reply_join(self, channel, name, topic, hmac, x, y, users):
        print "* Joined channel %s" % name
        self.send_channel_message(channel, "Hello!")

class SourceFactory(IbidSourceFactory):
    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        self.auth = {}
        self.log = logging.getLogger('source.%s' % self.name)
        keys = silc.create_key_pair("silc.pub", "silc.prv", passphrase = "")
        self.client = SilcBot(keys, "ibidot", "ibidbot", "Ibid Bot")
    
    def tick(self):
        self.client.run_one()

    def setServiceParent(self, service):
        s = internet.TimerService(0.2, self.tick)
        if service is None:
            s.startService()
        else:
            s.setServiceParent(service)

# vi: set et sta sw=4 ts=4:

