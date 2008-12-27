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

    encoding = 'latin-1'
        
    def connectionMade(self):
        self.nickname = ibid.config.sources[self.factory.name]['nick']
        irc.IRCClient.connectionMade(self)
        self.factory.resetDelay()
        self.factory.respond = self.respond
        self.factory.proto = self
        self.auth_callbacks = {}

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    def signedOn(self):
        if 'mode' in ibid.config.sources[self.factory.name]:
            self.mode(self.nickname, True, ibid.config.sources[self.factory.name]['mode'])
        for channel in ibid.config.sources[self.factory.name]['channels']:
            self.join(channel)

    def privmsg(self, user, channel, msg):
        nick = user.split('!', 1)[0]
        event = Event(self.factory.name, 'message')
        event.message = unicode(msg)
        event.sender = unicode(user)
        event.sender_id = unicode(nick)
        event.who = unicode(nick)
        event.channel = unicode(channel)
        event.source = self.factory.name

        if channel.lower() == self.nickname.lower():
            event.addressed = True
            event.public = False
            event.channel = event.who
        else:
            event.public = True

        ibid.dispatcher.dispatch(event)

    def userJoined(self, user, channel):
        event = Event(self.factory.name, 'state')
        nick = user.split('!', 1)[0]
        event.sender = unicode(user)
        event.sender_id = unicode(nick)
        event.who = unicode(nick)
        event.state = 'joined'
        event.channel = event.who
        ibid.dispatcher.dispatch(event)

    def respond(self, response):
        if 'action' in response and response['action']:
            self.me(response['target'].encode(encoding), response['reply'].encode(encoding))
        else:
            self.msg(response['target'].encode(encoding), response['reply'].encode(encoding))

        if 'ircaction' in response:
            (action, channel) = response['ircaction']
            if action == 'join':
                self.join(channel.encode(encoding))
            elif action == 'part':
                self.part(channel.encode(encoding))

    def authenticate(self, nick, callback):
        self.sendLine('WHOIS %s' % nick.encode(encoding))
        self.auth_callbacks[nick] = callback

    def do_auth_callback(self, nick, result):
        if nick in self.auth_callbacks:
            self.auth_callbacks[nick](nick, result)
            del self.auth_callbacks[nick]

    def irc_unknown(self, prefix, command, params):
        if command == '307' and len(params) == 3 and params[2] == 'is a registered nick':
            self.do_auth_callback(params[1], True)
        elif command == '307' and len(params) == 3 and params[2] == 'user has identified to services':
            self.do_auth_callback(params[1], True)
        elif command == '320' and len(params) == 3 and params[2] == 'is identified to services ':
            self.do_auth_callback(params[1], True)
        elif command == "RPL_ENDOFWHOIS":
            self.do_auth_callback(params[1], False)

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

    def disconnect(self):
        self.stopTrying()
        self.stopFactory()
        self.proto.transport.loseConnection()
        return True

# vi: set et sta sw=4 ts=4:
