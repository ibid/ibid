from fnmatch import fnmatch
from time import sleep
import logging

from twisted.internet import reactor
from twisted.words.protocols import irc
from twisted.internet import protocol, ssl
from twisted.application import internet
from sqlalchemy import or_

import ibid
from ibid.config import Option, IntOption, BoolOption, FloatOption, ListOption
from ibid.db.models import Credential
from ibid.source import IbidSourceFactory
from ibid.event import Event
from ibid.utils import ibid_version

class Ircbot(irc.IRCClient):

    _ping_deferred = None
    _reconnect_deferred = None

    def connectionMade(self):
        self.nickname = self.factory.nick.encode('utf-8')

        irc.IRCClient.connectionMade(self)

        self.factory.resetDelay()
        self.factory.proto = self
        self.auth_callbacks = {}
        self.mode_prefixes = '@+'
        self._ping_deferred = reactor.callLater(self.factory.ping_interval, self._idle_ping)
        self.factory.log.info(u"Connected")

    def connectionLost(self, reason):
        self.factory.log.info(u"Disconnected (%s)", reason)

        event = Event(self.factory.name, u'source')
        event.status = u'disconnected'
        ibid.dispatcher.dispatch(event)

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

        event = Event(self.factory.name, u'source')
        event.status = u'connected'
        ibid.dispatcher.dispatch(event)

    def _create_event(self, type, user, channel):
        nick = user.split('!', 1)[0]
        event = Event(self.factory.name, type)
        event.sender['connection'] = user
        event.sender['id'] = nick
        event.sender['nick'] = event.sender['id']
        event.channel = channel
        event.public = True
        return event

    def _state_event(self, user, channel, action, kicker=None, message=None, othername=None):
        event = self._create_event(u'state', user, channel)
        event.state = action
        if message:
            event.message = message
        if kicker:
            event.kicker = kicker
            self.factory.log.debug(u"%s has been kicked from %s by %s (%s)", event.sender['id'], event.channel, event.kicker, event.message)
        elif othername:
            event.othername = othername
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def privmsg(self, user, channel, msg):
        self._message_event(u'message', user, channel, msg)

    def noticed(self, user, channel, msg):
        self._message_event(u'notice', user, channel, msg)

    def action(self, user, channel, msg):
        self._message_event(u'action', user, channel, msg)

    def _message_event(self, msgtype, user, channel, msg):
        user = unicode(user, 'utf-8', 'replace')
        channel = unicode(channel, 'utf-8', 'replace')

        event = self._create_event(msgtype, user, channel)
        event.message = unicode(msg, 'utf-8', 'replace')
        self.factory.log.debug(u"Received %s from %s in %s: %s", msgtype, event.sender['id'], event.channel, event.message)

        if channel.lower() == self.nickname.lower():
            event.addressed = True
            event.public = False
            event.channel = event.sender['connection']
        else:
            event.public = True

        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def userJoined(self, user, channel):
        user = unicode(user, 'utf-8', 'replace')
        channel = unicode(channel, 'utf-8', 'replace')
        self._state_event(user, channel, u'online')

    def userLeft(self, user, channel):
        user = unicode(user, 'utf-8', 'replace')
        channel = unicode(channel, 'utf-8', 'replace')
        self._state_event(user, channel, u'offline')

    def userRenamed(self, oldname, newname):
        oldname = unicode(oldname, 'utf-8', 'replace')
        newname = unicode(newname, 'utf-8', 'replace')
        self._state_event(oldname, None, u'offline', othername=newname)
        self._state_event(newname, None, u'online', othername=oldname)

    def userQuit(self, user, channel):
        # Channel contains the quit message
        user = unicode(user, 'utf-8', 'replace')
        channel = unicode(channel, 'utf-8', 'replace')
        self._state_event(user, None, u'offline', message=channel)

    def userKicked(self, kickee, channel, kicker, message):
        kickee = unicode(kickee, 'utf-8', 'replace')
        channel = unicode(channel, 'utf-8', 'replace')
        kicker = unicode(kicker, 'utf-8', 'replace')
        message = unicode(message, 'utf-8', 'replace')
        self._state_event(kickee, channel, u'kicked', kicker, message)

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        message = response['reply']
        raw_message = message.encode('utf-8')

        # Target may be a connection or a plain nick
        target = response['target'].split('!')[0]
        raw_target = target.encode('utf-8')

        if response.get('topic', False):
            self.topic(raw_target, raw_message)
            self.factory.log.debug(u"Set topic in %s to %s", target, message)
        elif response.get('action', False):
            # We can't use self.me() because it prepends a # onto channel names
            # See http://twistedmatrix.com/trac/ticket/3910
            self.ctcpMakeQuery(raw_target, [('ACTION', raw_message)])
            self.factory.log.debug(u"Sent action to %s: %s", target, message)
        elif response.get('notice', False):
            self.notice(raw_target, raw_message)
            self.factory.log.debug(u"Sent notice to %s: %s", target, message)
        else:
            self.msg(raw_target, raw_message)
            self.factory.log.debug(u"Sent privmsg to %s: %s", target, message)

    def join(self, channel):
        self.factory.log.info(u"Joining %s", channel)
        irc.IRCClient.join(self, channel.encode('utf-8'))

    def joined(self, channel):
        event = Event(self.factory.name, u'source')
        event.channel = channel
        event.status = u'joined'
        ibid.dispatcher.dispatch(event)

    def leave(self, channel):
        self.factory.log.info(u"Leaving %s", channel)
        irc.IRCClient.leave(self, channel.encode('utf-8'))

    def left(self, channel):
        event = Event(self.factory.name, u'source')
        event.channel = channel
        event.status = u'left'
        ibid.dispatcher.dispatch(event)

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

    def irc_RPL_BOUNCE(self, prefix, params):
        # Broken in IrcClient :/
        # See http://twistedmatrix.com/trac/ticket/3285
        if params[-1] in ('are available on this server', 'are supported by this server'):
            self.isupport(params[1:-1])
        else:
            self.bounce(params[1])

    def isupport(self, options):
        "Server supports message"
        for option in options:
            if option.startswith('PREFIX='):
                self.mode_prefixes = option.split(')', 1)[1]

    def irc_RPL_NAMREPLY(self, prefix, params):
        channel = params[2]
        for user in params[3].split():
            if user[0] in self.mode_prefixes:
                user = user[1:]
            if user != self.nickname:
                self.userJoined(user, channel)

    def ctcpQuery_VERSION(self, user, channel, data):
        nick = user.split("!")[0]
        self.ctcpMakeReply(nick, [('VERSION', 'Ibid %s' % (ibid_version() or '',))])

    def ctcpQuery_SOURCE(self, user, channel, data):
        nick = user.split("!")[0]
        self.ctcpMakeReply(nick, [('SOURCE', 'http://ibid.omnia.za.net/')])


class SourceFactory(protocol.ReconnectingClientFactory, IbidSourceFactory):
    protocol = Ircbot

    auth = ('hostmask', 'nickserv')
    supports = ('action', 'notice', 'topic')

    port = IntOption('port', 'Server port number', 6667)
    ssl = BoolOption('ssl', 'Use SSL', False)
    server = Option('server', 'Server hostname')
    nick = Option('nick', 'IRC nick', ibid.config['botname'])
    modes = Option('modes', 'User modes to set')
    channels = ListOption('channels', 'Channels to autojoin', [])
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

    def leave(self, channel):
        return self.proto.leave(channel)

    def change_nick(self, nick):
        return self.proto.setNick(nick.encode('utf-8'))

    def send(self, response):
        return self.proto.send(response)

    def logging_name(self, identity):
        if identity is None:
            return u''
        return identity.split(u'!')[0]

    def message_max_length(self, response, event=None):
        return 490

    def url(self):
        return u'irc://%s@%s:%s' % (self.nick, self.server, self.port)

    def auth_hostmask(self, event, credential = None):
        for credential in event.session.query(Credential) \
                .filter_by(method=u'hostmask', account_id=event.account) \
                .filter(or_(Credential.source == event.source,
                            Credential.source == None)) \
                .all():
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
