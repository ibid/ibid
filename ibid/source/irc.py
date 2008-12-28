import re
from fnmatch import fnmatch
from time import sleep

from twisted.internet import reactor
from twisted.words.protocols import irc
from twisted.internet import protocol, ssl
from twisted.application import internet
from sqlalchemy import or_

import ibid
from ibid.models import Credential
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

    def _create_event(self, type, user, channel):
        nick = user.split('!', 1)[0]
        event = Event(self.factory.name, type)
        event.sender = unicode(user)
        event.sender_id = unicode(nick)
        event.who = unicode(nick)
        event.channel = unicode(channel)
        event.public = True
        event.source = self.factory.name
        return event

    def _state_event(self, user, channel, action, kicker=None, message=None):
        event = self._create_event('state', user, channel)
        event.channel = event.who
        event.state = action
        if kicker: event.kicker = kicker
        if message: event.message = message
        ibid.dispatcher.dispatch(event)

    def privmsg(self, user, channel, msg):
        event = self._create_event('message', user, channel)
        event.message = unicode(msg)

        if channel.lower() == self.nickname.lower():
            event.addressed = True
            event.public = False
            event.channel = event.who
        else:
            event.public = True

        ibid.dispatcher.dispatch(event)

    def userJoined(self, user, channel):
        self._state_event(user, channel, 'joined')

    def userLeft(self, user, channel):
        self._state_event(user, channel, 'parted')

    def userQuit(self, user, channel):
        self._state_event(user, channel, 'quit')

    def userKicked(self, kickee, channel, kicker, message):
        self._state_event(kickee, channel, 'kicked', kicker, message)

    def respond(self, response):
        if 'action' in response and response['action']:
            self.me(response['target'].encode(encoding), response['reply'].encode(encoding))
        else:
            self.msg(response['target'].encode(encoding), response['reply'].encode(encoding))

    def join(self, channel):
        irc.IRCClient.join(self, channel.encode(encoding))

    def part(self, channel):
        irc.IRCClient.part(self, channel.encode(encoding))

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
        self.auth = {}

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

    def join(self, channel):
        return self.proto.join(channel)

    def part(self, channel):
        return self.proto.part(channel)

    def auth_hostmask(self, event, credential = None):
        session = ibid.databases.ibid()
        for credential in session.query(Credential).filter_by(method='hostmask').filter_by(account_id=event.account).filter(or_(Credential.source == event.source, Credential.source == None)).all():
            if fnmatch(event.sender, credential.credential):
                return True

    def _irc_auth_callback(self, nick, result):
        self.auth[nick] = result

    def auth_nickserv(self, event, credential):
        reactor.callFromThread(self.proto.authenticate, event.who, self._irc_auth_callback)
        for i in xrange(150):
            if event.who in self.auth:
                break
            sleep(0.1)

        if event.who in self.auth:
            result = self.auth[event.who]
            del self.auth[event.who]
            return result

# vi: set et sta sw=4 ts=4:
