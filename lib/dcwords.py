#!/usr/bin/env python
# Copyright 2009 Stefano Rivera <scripts@rivera.za.net>
# Released under the MIT license

# Speaks NMDC protocol. Not widely tested.
# Assumes the hub uses UTF-8. Client interface uses unicode()
# Currently only implements chat, not file transfer
# a chatroom of None == public chat

import re

from twisted.protocols.basic import LineReceiver
from twisted.internet import protocol, reactor
import logging

log = logging.getLogger('dcclient')

class User(object):
    "Represents a client connected to the hub"
    def __init__(self, name):
        self.name = name
        for key in 'interest,client,upload_limit,download_limit,hubs,mode,auto_open,slots,client,mode,connection,away,email,sharesize,bot,op'.split(','):
            setattr(self, key, None)

class DCClient(LineReceiver):

    # Configuration:

    # Attempt to keep the connection alive with periodic $GetNickLists
    # if idle (rare on a busy server)
    keepalive = True
    ping_interval = 180
    pong_timeout = 180

    # Client information (mostly simply provided to server)
    my_nickname = 'foo'
    my_password = None
    my_interest = ''
    my_speed = '1kbps'
    my_email = ''
    my_away = 'normal'
    my_sharesize = 0
    my_mode = 'active'
    my_hubs = (0, 0, 1)
    my_slots = 0
    old_version = '1.2'
    client = 'TwisteDC'
    version = 'dev'
    auto_open = None

    # Server Properties
    hub_name = ''
    hub_topic = ''
    hub_motd = ''
    hub_tagline = ''
    hub_supports = ()
    hub_users = {}

    # LineReceiver:
    delimiter = '|'

    # State:
    finished_handshake = False
    _ping_deferred = None
    _reconnect_deferred = None

    # Callbacks:
    def yourHost(self, name, topic, tagline, motd):
        "Called with information about the server"

    def bounce(self, destination):
        """Called with information about where the client should reconnect
        or None, if the server is trying to get rid of us"""

    def isupport(self, options):
        "Called with extenisons the server supports"

    def privmsg(self, user, private, message):
        "Called when I have a message from a user to me or the chat"

    def action(self, user, private, message):
        "Called when I see an action in private or chat"

    def signedOn(self):
        "Called when successfully signed on"

    def userJoined(self, user):
        "Called when a user joins"

    def userQuit(self, user):
        "Called when a user leaves"

    def topicUpdated(self, topic):
        "Called when the topic is changed"

    # Actions:
    def say(self, user, message):
        "Send a message to a user or chat if user=None"
        if user is None:
            self.sendLine('<%s> %s' % (
                _encode_htmlent(self.my_nickname, '>'), _encode_htmlent(message)
            ))
        else:
            self.sendLine('$To: %s From: %s $<%s> %s' % (
                _encode_htmlent(user, ' '),
                _encode_htmlent(self.my_nickname, ' '),
                _encode_htmlent(self.my_nickname, '>'),
                _encode_htmlent(message),
            ))

    def away(self, away='away'):
        "Update the away status. For possible statuses, see _away"
        self.away = away
        self._sendMyINFO()

    def back(self):
        "Return to normal away status"
        self.away = 'normal'
        self._sendMyINFO()

    # Code:
    # High Level Protocol:
    def dc_HubIsFull(self, params):
        log.debug("Hub is full")

    def dc_Lock(self, params):
        "Calculate the NMDC Lock code"
        challange = params.split(' ', 1)[0]
        
        key = {}
        for i in xrange(1, len(challange)):
            key[i] = ord(challange[i]) ^ ord(challange[i-1])
        key[0] = ord(challange[0]) ^ ord(challange[len(challange)-1]) ^ ord(challange[len(challange)-2]) ^ 5
        for i in xrange(0, len(challange)):
            key[i] = ((key[i]<<4) & 240) | ((key[i]>>4) & 15)
        response = ""
        for i in xrange(0, len(key)):
            if key[i] in (0, 5, 36, 96, 124, 126):
                response += "/%%DCN%03d%%/" % (key[i],)
            else:
                response += chr(key[i])
    
        if challange.startswith('EXTENDEDPROTOCOL'):
            self.sendLine('$Supports HubTopic QuickList NoHello')

        self.sendLine('$Key ' + response)

        if not challange.startswith('EXTENDEDPROTOCOL'):
            self.sendLine('$ValidateNick ' + _encode_htmlent(self.my_nickname))
        # Otherwise defer registration to dc_Supports

    def dc_HubName(self, params):
        "Connected / Hub Name Changed"
        self.hub_name = _decode_htmlent(params)

        if 'HubTopic' not in self.hub_supports:
            self.topicUpdated(self.hub_name)

    def dc_HubTopic(self, params):
        "Hub Topic changed"
        self.hub_topic = _decode_htmlent(params)
        self.topicUpdated(self.hub_topic)

    def dc_Supports(self, params):
        "Hub Extensions"
        self.hub_supports = params.split(' ')
        self.isupport(self.hub_supports)

        if 'QuickList' not in self.hub_supports:
            self.sendLine('$ValidateNick ' + _encode_htmlent(self.my_nickname))
        elif self.my_password:
            self._sendMyINFO()

        if self.my_password is None:
            if 'QuickList' not in self.hub_supports:
                self.sendLine('$Version ' + _encode_htmlent(self.old_version))
                self.sendLine('$GetNickList')

            self._sendMyINFO()

    def dc_ValidateDenide(self, params):
        "Server didn't like the nick, try another"
        self.my_nickname += '_'
        log.error('Nickname rejected, trying %s', self.my_nickname)
        self.sendLine('$ValidateNick ' + _encode_htmlent(self.my_nickname))

    def dc_Hello(self, params):
        "Someone arrived"
        nick = _decode_htmlent(params)
        if nick not in self.hub_users:
            self.hub_users[nick] = User(nick)
            self.userJoined(nick)

    def dc_GetPass(self, params):
        "Password requested"
        self.sendLine('$MyPass ' + _encode_htmlent(self.my_password))

    def dc_BadPass(self, params):
        "Password rejected"
        log.error('Password rejected')

    def dc_LogedIn(self, params):
        "Password accepted"
        if 'QuickList' not in self.hub_supports:
            self.sendLine('$Version ' + _encode_htmlent(self.old_version))
            self.sendLine('$GetNickList')

        self._sendMyINFO()

    _myinfo_re = re.compile(r'^\$ALL (\S*) (.*?)(?:<(\S*) ([A-Z0-9.:,/]*)>)?\$([AP5 ])\$([^$]*)([^$])\$([^$]*)\$(\d*)\$$')
    def dc_MyINFO(self, params):
        "Information about a user"
        self._state_Connected()

        m = self._myinfo_re.match(params)
        if not m:
            log.error("Couldn't decode MyINFO: %s", params)
            return

        nick = _decode_htmlent(m.group(1))
        if nick in self.hub_users:
            user = self.hub_users[nick]
        else:
            user = User(nick)
        user.my_interest = _decode_htmlent(m.group(2))
        user.client = (m.group(3) and _decode_htmlent(m.group(3)) or None, None)

        if m.group(4):
            for taglet in _decode_htmlent(m.group(4)).split(','):
                try:
                    key, value = taglet.split(':', 1)
                    if key in ('B', 'L'):
                        user.upload_limit = float(value)
                    elif key == 'F':
                        user.download_limit, user.upload_limit = value.split('/', 1)
                    elif key == 'H':
                        user.hubs = value.split('/')
                    elif key == 'M':
                        user.mode = _rmodes[value]
                    elif key == 'O':
                        user.auto_open = float(value)
                    elif key == 'S':
                        user.slots = int(value)
                    elif key == 'V':
                        user.client = (m.group(3), value)
                    else:
                        log.error('Unknown tag key: %s:%s on user %s', key, value, nick)
                except:
                    log.exception('Error parsing tag: %s', m.group(4))

        if m.group(5) in _rmodes:
            user.mode = _rmodes[m.group(5)]

        user.connection = _decode_htmlent(m.group(6))
        user.away = m.group(7) in _raway and _raway[m.group(7)] or 'normal'
        user.email = _decode_htmlent(m.group(8))
        user.sharesize = int(m.group(9))

        if nick not in self.hub_users:
            self.hub_users[nick] = user
            self.userJoined(nick)
    
    def dc_OpList(self, params):
        "List of Ops received"
        for nick in params.split('$$'):
            nick = _decode_htmlent(nick)
            user = nick in self.hub_users and self.hub_users[nick] or User(nick)
            user.op = True
            if nick not in self.hub_users:
                self.hub_users[nick] = user
                self.userJoined(nick)

    def dc_BotList(self, params):
        "List of Bots received"
        for nick in params.split('$$'):
            nick = _decode_htmlent(nick)
            user = nick in self.hub_users and self.hub_users[nick] or User(nick)
            user.bot = True
            if nick not in self.hub_users:
                self.hub_users[nick] = user
                self.userJoined(nick)

    def dc_NickList(self, params):
        "List of connected users received"
        self._state_Connected()

        oldlist = set(self.hub_users.keys())

        for nick in params.split('$$'):
            nick = _decode_htmlent(nick)
            user = nick in self.hub_users and self.hub_users[nick] or User(nick)
            if nick in self.hub_users:
                oldlist.remove(nick)
            else:
                self.hub_users[nick] = user
                self.userJoined(nick)

        for nick in oldlist:
            self.userQuit(nick)
            del self.hub_users[nick]

        if self._reconnect_deferred:
            log.log(logging.DEBUG - 5, u'Received PONG')
            self._reconnect_deferred.cancel()
            self._reconnect_deferred = None
            self._ping_deferred = reactor.callLater(self.ping_interval, self._idle_ping)

    def dc_ConnectToMe(self, params):
        "Someone wants to connect to me"
        #TODO

    def dc_RevConnectToMe(self, params):
        "Someone wants me to connect to them"
        #TODO

    def dc_Quit(self, params):
        "Someone has gone home"
        nick = _decode_htmlent(params)
        if nick in self.hub_users:
            self.userQuit(nick)
            del self.hub_users[nick]

    def dc_Search(self, params):
        "Someone wants to find something"
        #TODO

    def dc_ForceMove(self, params):
        "Redirecting elsewhere"
        self.bounce(params and _decode_htmlent(params) or None)

    def dc_UserCommand(self, params):
        "Menu of Hub specific commands"
        #TODO

    def dc_UserIP(self, params):
        "I asked for an IP, here it is"
        #TODO

    _to_re = re.compile(r'^.*? From: ([^$]*?) \$<[^>]*?> (.*)$')
    def dc_To(self, params):
        "Received a private message"
        m = self._to_re.match(params)
        
        if m is None:
            log.error('Cannot parse message: %s', params)
            return
        
        self.privmsg(_decode_htmlent(m.group(1)), True, _decode_htmlent(m.group(2)))

    # Helpers:
    def _state_Connected(self):
        "Update the state that we are now connected and won't be reciveing MOTD any more"
        if not self.finished_handshake:
            self.finished_handshake = True
            self.yourHost(self.hub_name, self.hub_topic, self.hub_tagline, self.hub_motd)
            self.signedOn()

    def _sendMyINFO(self):
        "Tell the server all about me"
        tags = []
        if self.version:
            tags.append('V:' + self.version)
        if self.my_mode in _modes.keys():
            tags.append('M:' + _modes[self.my_mode])
        if self.my_hubs:
            tags.append('H:' + '/'.join(str(x) for x in self.my_hubs))
        if self.my_slots:
            tags.append('S:%i' % self.my_slots)
        if self.auto_open:
            tags.append('O:' + self.auto_open)

        tag = '%s %s' % (self.client, ','.join(tags))

        away = _away[self.my_away]

        self.sendLine('$MyINFO $ALL %s %s<%s>$ $%s%s$%s$%s$' % (
            _encode_htmlent(self.my_nickname, ' '),
            _encode_htmlent(self.my_interest),
            _encode_htmlent(tag),
            _encode_htmlent(self.my_speed),
            away,
            _encode_htmlent(self.my_email),
            self.my_sharesize,
        ))

    def _idle_ping(self):
        "Fired when idle and keepalive is enabled"
        log.log(logging.DEBUG - 5, u'Sending idle PING')
        self._ping_deferred = None
        self._reconnect_deferred = reactor.callLater(self.pong_timeout, self._timeout_reconnect)
        self.sendLine('$GetNickList')

    def _timeout_reconnect(self):
        "Fired when pong never recived"
        info(u'Ping-Pong timeout. Reconnecting')
        self.transport.loseConnection()

    # Low Level Protocol:
    def connectionMade(self):
        if self.keepalive:
            self._ping_deferred = reactor.callLater(self.ping_interval, self._idle_ping)
    
    def sendLine(self, line):
        if self._ping_deferred:
            self._ping_deferred.reset(self.ping_interval)
        return LineReceiver.sendLine(self, line)
    
    def lineReceived(self, line):
        if self._ping_deferred:
            self._ping_deferred.reset(self.ping_interval)

        if line.strip() == '':
            return
        elif line[0] == '$':
            command = line[1:].split(' ', 1)[0]
            params = ' ' in line and line[1:].split(' ', 1)[1] or None
            handler = getattr(self, 'dc_' + command.strip(':'), None)
            if handler:
                handler(params)
            else:
                log.error('Unhandled command received: %s', command)
                return
        elif line[0] == '<':
            speaker, message = line[1:].split('>', 1)
            speaker = _decode_htmlent(speaker)
            message = _decode_htmlent(message[1:])

            if not self.finished_handshake:
                if not self.hub_tagline:
                    self.hub_tagline = message
                else:
                    self.hub_motd += message + '\n'
            else:
                if speaker != self.my_nickname:
                    self.privmsg(speaker, False, message)
        elif line.startswith('* ') or line.startswith('** '):
            speaker, message = line.split(' ', 2)[1:]
            speaker = _decode_htmlent(speaker)
            message = _decode_htmlent(message)
            if speaker != self.my_nickname:
                self.action(speaker, False, message)
        else:
            log.error('Unrecognised command received: %s', line)
            return

def _encode_htmlent(message, extra_enc=''):
    "DC uses HTML entities to encode non-ASCII text. Encode."
    if isinstance(message, unicode):
        message = message.encode('utf-8')

    replace = lambda match: '&#%i;' % ord(match.group(1))
    return re.sub(r'([$|%s])' % extra_enc, replace, message)

def _decode_htmlent(message):
    "DC uses HTML entities to encode non-ASCII text. Decode." 
    replace = lambda match: unichr(int(match.group(1)))
    message = unicode(message, 'utf-8', 'replace')
    message = re.sub(r'&#(\d+);', replace, message)
    return re.sub(r'/%DCN(\d{3})%/', replace, message)

_modes = {
    'active': 'A',
    'passive': 'P',
    'socks': '5',
}
_rmodes = dict((y, x) for x, y in _modes.iteritems())

_away = {
    'normal': chr(1),
    'away': chr(2),
    'server': chr(4),
    'server away': chr(6),
    'fireball': chr(8),
    'fireball away': chr(10),
}
_raway = dict((y, x) for x, y in _away.iteritems())
_raway.update({
    chr(3): 'away',
    chr(5): 'server',
    chr(7): 'server away',
    chr(9): 'fireball',
    chr(11): 'fireball away',
})

# Small testing framework:
def main():
    logging.basicConfig(level=logging.NOTSET)
    class DCFactory(protocol.ClientFactory):
        protocol = DCClient

        def clientConnectionLost(self, connector, reason):
            log.info('Lost')
            reactor.stop()

        def clientConnectionFailed(self, connector, reason):
            log.info('Failed')
            reactor.stop()
    
    f = DCFactory()
    reactor.connectTCP('localhost', 411, f)

    reactor.run()

if __name__ == '__main__':
    main()

# vi: set et sta sw=4 ts=4:
