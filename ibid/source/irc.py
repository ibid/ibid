import re
from fnmatch import fnmatch
from time import sleep
import logging

from twisted.internet import reactor
from twisted.words.protocols import irc
from twisted.internet import protocol, ssl
from twisted.application import internet
from sqlalchemy import or_

import ibid
from ibid.models import Credential
from ibid.source import IbidSourceFactory
from ibid.event import Event

encoding = 'utf-8'

class Ircbot(irc.IRCClient):

    def connectionMade(self):
        self.nickname = ibid.config.sources[self.factory.name]['nick'].encode(encoding)
        irc.IRCClient.connectionMade(self)
        self.factory.resetDelay()
        self.factory.send = self.send
        self.factory.proto = self
        self.auth_callbacks = {}
        self.factory.log.info(u"Connected")

    def connectionLost(self, reason):
        self.factory.log.info(u"Disconnected (%s", reason)
        irc.IRCClient.connectionLost(self, reason)

    def signedOn(self):
        if 'mode' in ibid.config.sources[self.factory.name]:
            self.mode(self.nickname, True, ibid.config.sources[self.factory.name]['mode'].encode(encoding))
        for channel in ibid.config.sources[self.factory.name]['channels']:
            self.join(channel.encode(encoding))
        self.factory.log.info(u"Signed on")

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
        event = self._create_event(u'state', user, channel)
        event.state = action
        if kicker: event.kicker = kicker
        if message: event.message = message
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def privmsg(self, user, channel, msg):
        self.factory.log.debug(u"Received privmsg from %s in %s: %s", user, channel, msg)
        self._message_event(u'message', user, channel, msg)

    def noticed(self, user, channel, msg):
        self.factory.log.debug(u"Received notice from %s in %s: %s", user, channel, msg)
        self._message_event(u'notice', user, channel, msg)

    def _message_event(self, msgtype, user, channel, msg):
        event = self._create_event(msgtype, user, channel)
        event.message = unicode(msg)

        if channel.lower() == self.nickname.lower():
            event.addressed = True
            event.public = False
            event.channel = event.who
        else:
            event.public = True

        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def userJoined(self, user, channel):
        self.factory.log.debug(u"%s has joined %s", user, channel)
        self._state_event(user, channel, u'joined')

    def userLeft(self, user, channel):
        self.factory.log.debug(u"%s has left %s", user, channel)
        self._state_event(user, channel, u'parted')

    def userQuit(self, user, channel):
        self.factory.log.debug(u"%s has quit %s", user, channel)
        self._state_event(user, channel, u'quit')

    def userKicked(self, kickee, channel, kicker, message):
        self.factory.log.debug(u"%s has been kicked from %s by %s (%s)", kickee, channel, kicker, message)
        self._state_event(kickee, channel, u'kicked', kicker, message)

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        message = response['reply'].encode(encoding).replace('\n', ' ')[:490]
        if 'action' in response and response['action']:
            self.me(response['target'].encode(encoding), message)
            self.factory.log.debug(u"Sent action to %s: %s", response['target'], message)
        else:
            self.msg(response['target'].encode(encoding), message)
            self.factory.log.debug(u"Sent privmsg to %s: %s", response['target'], message)

    def join(self, channel):
        self.factory.log.info(u"Joining %s", channel)
        irc.IRCClient.join(self, channel.encode(encoding))

    def part(self, channel):
        self.factory.log.info(u"Leaving %s", channel)
        irc.IRCClient.part(self, channel.encode(encoding))

    def authenticate(self, nick, callback):
        self.sendLine('WHOIS %s' % nick.encode(encoding))
        self.auth_callbacks[nick] = callback

    def do_auth_callback(self, nick, result):
        if nick in self.auth_callbacks:
            self.factory.log.debug(u"Authentication result for %s: %s", nick, result)
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

    port = 6667
    ssl = False
    server = None

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        self.auth = {}
        self.log = logging.getLogger('source.%s' % self.name)

    def setServiceParent(self, service):
        if self.ssl:
            sslctx = ssl.ClientContextFactory()
            if service:
                internet.SSLClient(self.server, self.port, self, sslctx).setServiceParent(service)
            else:
                reactor.connectSSL(self.server, self.port, self, sslctx)
        else:
            if service:
                internet.TCPClient(self.server, self.port, self).setServiceParent(service)
            else:
                reactor.connectTCP(self.server, self.port, self)

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

    def change_nick(self, nick):
        return self.proto.setNick(nick.encode('utf-8'))

    def auth_hostmask(self, event, credential = None):
        session = ibid.databases.ibid()
        for credential in session.query(Credential).filter_by(method=u'hostmask').filter_by(account_id=event.account).filter(or_(Credential.source == event.source, Credential.source == None)).all():
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
