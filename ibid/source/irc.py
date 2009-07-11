from fnmatch import fnmatch
from time import sleep
import logging

from twisted.internet import reactor
from twisted.words.protocols import irc
from twisted.internet import protocol, ssl
from twisted.application import internet
from sqlalchemy import or_
from pkg_resources import resource_exists, resource_string

import ibid
from ibid.config import Option, IntOption, BoolOption, FloatOption
from ibid.models import Credential
from ibid.source import IbidSourceFactory
from ibid.event import Event

class Ircbot(irc.IRCClient):

    versionNum = resource_exists(__name__, '../.version') and resource_string(__name__, '../.version') or ''
    _ping_deferred = None
    _reconnect_deferred = None

    def connectionMade(self):
        self.nickname = self.factory.nick.encode('utf-8')
        irc.IRCClient.connectionMade(self)
        self.factory.resetDelay()
        self.factory.send = self.send
        self.factory.proto = self
        self.auth_callbacks = {}
        self._ping_deferred = reactor.callLater(self.factory.ping_interval, self._idle_ping)
        self.factory.log.info(u"Connected")

    def connectionLost(self, reason):
        self.factory.log.info(u"Disconnected (%s)", reason)
        irc.IRCClient.connectionLost(self, reason)

    def _idle_ping(self):
        self.factory.log.log(logging.DEBUG - 5, u'Sending idle PING')
        self._ping_deferred = None
        self._reconnect_deferred = reactor.callLater(self.factory.pong_timeout, self._timeout_reconnect)
        self.sendLine('PING idle-ibid')

    def _timeout_reconnect(self):
        self.factory.log.info(u'Ping-Pong timeout. Reconnecting')
        self.transport.loseConnection()

    def irc_PONG(self, prefix, params):
        if params[-1] == 'idle-ibid' and self._reconnect_deferred is not None:
            self.factory.log.log(logging.DEBUG - 5, u'Received PONG')
            self._reconnect_deferred.cancel()
            self._reconnect_deferred = None
            self._ping_deferred = reactor.callLater(self.factory.ping_interval, self._idle_ping)
        
    def dataReceived(self, data):
        irc.IRCClient.dataReceived(self, data)
        if self._ping_deferred is not None:
            self._ping_deferred.reset(self.factory.ping_interval)

    def sendLine(self, line):
        irc.IRCClient.sendLine(self, line)
        if self._ping_deferred is not None:
            self._ping_deferred.reset(self.factory.ping_interval)

    def signedOn(self):
        names = ibid.config.plugins['core']['names']
        if self.nickname not in names:
            self.factory.log.info(u'Adding "%s" to plugins.core.names', self.nickname)
            names.append(self.nickname)
            ibid.config.plugins['core']['names'] = names
            ibid.reloader.reload_config()
        if self.factory.modes:
            self.mode(self.nickname, True, self.factory.modes.encode('utf-8'))
        for channel in self.factory.channels:
            self.join(channel.encode('utf-8'))
        self.factory.log.info(u"Signed on")

    def _create_event(self, type, user, channel):
        nick = user.split('!', 1)[0]
        event = Event(self.factory.name, type)
        event.sender['connection'] = unicode(user, 'utf-8', 'replace')
        event.sender['id'] = unicode(nick, 'utf-8', 'replace')
        event.sender['nick'] = event.sender['id']
        event.channel = unicode(channel, 'utf-8', 'replace')
        event.public = True
        event.source = self.factory.name
        return event

    def _state_event(self, user, channel, action, kicker=None, message=None):
        event = self._create_event(u'state', user, channel)
        event.state = action
        if message:
            event.message = unicode(message, 'utf-8', 'replace')
        if kicker:
            event.kicker = unicode(kicker, 'utf-8', 'replace')
            self.factory.log.debug(u"%s has been kicked from %s by %s (%s)", event.sender['id'], event.channel, event.kicker, event.message)
        else:
            self.factory.log.debug(u"%s has %s %s", user, action, channel)
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def privmsg(self, user, channel, msg):
        self._message_event(u'message', user, channel, msg)

    def noticed(self, user, channel, msg):
        self._message_event(u'notice', user, channel, msg)

    def action(self, user, channel, msg):
        self._message_event(u'action', user, channel, msg)

    def _message_event(self, msgtype, user, channel, msg):
        event = self._create_event(msgtype, user, channel)
        event.message = unicode(msg, 'utf-8', 'replace')
        self.factory.log.debug(u"Received %s from %s in %s: %s", msgtype, event.sender['id'], event.channel, event.message)

        if channel.lower() == self.nickname.lower():
            event.addressed = True
            event.public = False
            event.channel = event.sender['nick']
        else:
            event.public = True

        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def userJoined(self, user, channel):
        self._state_event(user, channel, u'online')

    def userLeft(self, user, channel):
        self._state_event(user, channel, u'offline')

    def userQuit(self, user, channel):
        # Channel contains the quit message
        self._state_event(user, '', u'offline', message=channel)

    def userKicked(self, kickee, channel, kicker, message):
        self._state_event(kickee, channel, u'kicked', kicker, message)

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        message = response['reply'].replace('\n', ' ')[:490]
        if 'action' in response and response['action']:
            # We can't use self.me() because it prepends a # onto channel names
            self.ctcpMakeQuery(response['target'].encode('utf-8'), [('ACTION', message.encode('utf-8'))])
            self.factory.log.debug(u"Sent action to %s: %s", response['target'], message)
        else:
            if response.get('notice', False):
                send = self.notice
            else:
                send = self.msg
            send(response['target'].encode('utf-8'), message.encode('utf-8'))
            self.factory.log.debug(u"Sent privmsg to %s: %s", response['target'], message)

    def join(self, channel):
        self.factory.log.info(u"Joining %s", channel)
        irc.IRCClient.join(self, channel.encode('utf-8'))

    def part(self, channel):
        self.factory.log.info(u"Leaving %s", channel)
        irc.IRCClient.part(self, channel.encode('utf-8'))

    def authenticate(self, nick, callback):
        self.sendLine('WHOIS %s' % nick.encode('utf-8'))
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

    def ctcpQuery_VERSION(self, user, channel, data):
        nick = user.split("!")[0]
        self.ctcpMakeReply(nick, [('VERSION', 'Ibid %s' % self.versionNum)])

    def ctcpQuery_SOURCE(self, user, channel, data):
        nick = user.split("!")[0]
        self.ctcpMakeReply(nick, [('SOURCE', 'http://ibid.omnia.za.net/')])

class SourceFactory(protocol.ReconnectingClientFactory, IbidSourceFactory):
    protocol = Ircbot

    auth = ('hostmask', 'nickserv')
    supports = ('action',)

    port = IntOption('port', 'Server port number', 6667)
    ssl = BoolOption('ssl', 'Use SSL', False)
    server = Option('server', 'Server hostname')
    nick = Option('nick', 'IRC nick', ibid.config['botname'])
    modes = Option('modes', 'User modes to set')
    channels = Option('channels', 'Channels to autojoin', [])
    ping_interval = FloatOption('ping_interval', 'Seconds idle before sending a PING', 60)
    pong_timeout = FloatOption('pong_timeout', 'Seconds to wait for PONG', 300)
    # ReconnectingClient uses this:
    maxDelay = IntOption('max_delay', 'Max seconds to wait inbetween reconnects', 900)
    factor = FloatOption('delay_factor', 'Factor to multiply delay inbetween reconnects by', 2)

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        self._auth = {}
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
        if hasattr(self, 'proto'):
            self.proto.transport.loseConnection()
        return True

    def join(self, channel):
        return self.proto.join(channel)

    def part(self, channel):
        return self.proto.part(channel)

    def change_nick(self, nick):
        return self.proto.setNick(nick.encode('utf-8'))

    def url(self):
        return u'irc://%s@%s:%s' % (self.nick, self.server, self.port)

    def auth_hostmask(self, event, credential = None):
        for credential in event.session.query(Credential) \
                .filter_by(method=u'hostmask').filter_by(account_id=event.account) \
                .filter(or_(Credential.source == event.source, Credential.source == None)).all():
            if fnmatch(event.sender['connection'], credential.credential):
                return True

    def _irc_auth_callback(self, nick, result):
        self._auth[nick] = result

    def auth_nickserv(self, event, credential):
        reactor.callFromThread(self.proto.authenticate, event.sender['nick'], self._irc_auth_callback)
        for i in xrange(150):
            if event.sender['nick'] in self._auth:
                break
            sleep(0.1)

        if event.sender['nick'] in self._auth:
            result = self._auth[event.sender['nick']]
            del self._auth[event.sender['nick']]
            return result

# vi: set et sta sw=4 ts=4:
