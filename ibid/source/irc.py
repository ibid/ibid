import re

from twisted.internet import reactor
from twisted.words.protocols import irc
from twisted.internet import protocol, ssl
from twisted.application import internet

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

encoding = 'latin-1'

class Ircbot(irc.IRCClient):
        
    def connectionMade(self):
        self.nickname = ibid.config.sources[self.factory.name]['nick']
        irc.IRCClient.connectionMade(self)
        self.factory.resetDelay()
        self.factory.respond = self.respond

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    def signedOn(self):
        self.mode(self.nickname, True, 'B')
        for channel in ibid.config.sources[self.factory.name]['channels']:
            self.join(channel)

    def privmsg(self, user, channel, msg):
        user = user.split('!', 1)[0]
        event = Event(self.factory.name, 'message')
        event.message = msg
        event.user = user
        event.channel = channel
        event.source = self.factory.name

        if channel.lower() == self.nickname.lower():
            event.addressed = True
            event.public = False
            event.channel = user
        else:
            event.public = True

        ibid.dispatcher.dispatch(event)

    def userJoined(self, user, channel):
        event = Event(self.factory.name, 'state')
        event.user = user,
        event.state = 'joined'
        event.channel = channel
        ibid.dispatcher.dispatch(event)

    def respond(self, response):
        if 'action' in response and response['action']:
            self.me(response['target'], response['reply'].encode(encoding))
        else:
            self.msg(response['target'], response['reply'].encode(encoding))

        if 'ircaction' in response:
            (action, channel) = response['ircaction']
            if action == 'join':
                self.join(channel)
            elif action == 'part':
                self.part(channel)

class SourceFactory(protocol.ReconnectingClientFactory, IbidSourceFactory):
    protocol = Ircbot

    def __init__(self, name):
        self.name = name
        self.respond = None

    def setServiceParent(self, service):
        port = 6667
        server = ibid.config.sources[self.name]['server']

        if 'port' in ibid.config.sources[self.name]:
            port = ibid.config.sources[self.name]['port']

        if 'ssl' in ibid.config.sources[self.name] and ibid.config.sources[self.name]['ssl']:
            sslctx = ssl.ClientContextFactory()
            if service:
                internet.SSLClient(server, port, self, sslctx).setServiceParent(service)
            else:
                reactor.connectSSL(server, port, self, sslctx)
        else:
            if service:
                internet.TCPClient(server, port, self).setServiceParent(service)
            else:
                reactor.connectTCP(server, port, self)

    def connect(self):
        return self.setServiceParent(None)

# vi: set et sta sw=4 ts=4:
