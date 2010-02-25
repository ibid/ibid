# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import logging

from wokkel import client, xmppim, subprotocols
from twisted.internet import protocol, reactor, ssl
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish

import ibid
from ibid.config import Option, BoolOption, IntOption, ListOption
from ibid.source import IbidSourceFactory
from ibid.event import Event

class Message(domish.Element):

    def __init__(self, to, frm, body, type):
        domish.Element(self, (None, 'message'))
        self['to'] = to
        self['from'] = frm
        self['type'] = 'chat'
        self.addElement('body', content=body)


class JabberBot(xmppim.MessageProtocol, xmppim.PresenceClientProtocol, xmppim.RosterClientProtocol):

    def __init__(self):
        xmppim.MessageProtocol.__init__(self)
        self.rooms = []

    def connectionInitialized(self):
        self.parent.log.info(u"Connected")
        xmppim.MessageProtocol.connectionInitialized(self)
        xmppim.PresenceClientProtocol.connectionInitialized(self)
        xmppim.RosterClientProtocol.connectionInitialized(self)
        self.xmlstream.send(xmppim.AvailablePresence())
        self.roster = self.getRoster() #See section 7.3 of http://www.ietf.org/rfc/rfc3921.txt
        self.name = self.parent.name
        self.parent.send = self.send
        self.parent.proto = self
        for room in self.parent.rooms:
            self.join(room)

        event = Event(self.parent.name, u'source')
        event.status = u'connected'
        ibid.dispatcher.dispatch(event)

    def connectionLost(self, reason):
        self.parent.log.info(u"Disconnected (%s)", reason)

        event = Event(self.parent.name, u'source')
        event.status = u'disconnected'
        ibid.dispatcher.dispatch(event)

        subprotocols.XMPPHandler.connectionLost(self, reason)

    def _state_event(self, entity, state):
        event = Event(self.name, u'state')
        event.state = state
        if entity.userhost().lower() in self.rooms:
            nick = entity.full().split('/')[1]
            event.channel = entity.userhost()
            if nick == self.parent.nick:
                event.type = u'connection'
                event.status = state == u'online' and u'joined' or u'left'
            else:
                event.sender['connection'] = entity.full()
                event.sender['id'] = event.sender['connection']
                event.sender['nick'] = nick
                event.public = True
        else:
            event.sender['connection'] = entity.full()
            event.sender['id'] = event.sender['connection'].split('/')[0]
            event.sender['nick'] = event.sender['connection'].split('@')[0]
            event.channel = entity.full()
            event.public = False
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def _onPresenceAvailable(self, presence):
        entity = JID(presence["from"])

        show = unicode(presence.show or '')
        if show not in ['away', 'xa', 'chat', 'dnd']:
            show = None

        statuses = self._getStatuses(presence)

        try:
            priority = int(unicode(presence.priority or '')) or 0
        except ValueError:
            priority = 0

        self.availableReceived(entity, show, statuses, priority)

    def availableReceived(self, entity, show=None, statuses=None, priority=0):
        self.parent.log.debug(u"Received available presence from %s (%s)", entity.full(), show)
        self._state_event(entity, u'online')

    def unavailableReceived(self, entity, statuses):
        self.parent.log.debug(u"Received unavailable presence from %s", entity.full())
        self._state_event(entity, u'offline')

    def subscribeReceived(self, entity):
        response = xmppim.Presence(to=entity, type='subscribed')
        self.xmlstream.send(response)
        response = xmppim.Presence(to=entity, type='subscribe')
        self.xmlstream.send(response)
        self.parent.log.info(u"Received and accepted subscription request from %s", entity.full())

    def onMessage(self, message):
        self.parent.log.debug(u"Received %s message from %s: %s", message['type'], message['from'], message.body)

        if message.x and message.x.defaultUri == 'jabber:x:delay':
            self.parent.log.debug(u"Ignoring delayed message")
            return

        if self.parent.accept_domains:
            if message['from'].split('/')[0].split('@')[1] not in self.parent.accept_domains:
                self.parent.log.info(u"Ignoring message because sender is not in accept_domains")
                return

        if message.body is None:
            self.parent.log.info(u'Ignoring empty message')
            return

        event = Event(self.parent.name, u'message')
        event.message = unicode(message.body)
        event.sender['connection'] = message['from']

        if message['type'] == 'groupchat':
            event.sender['id'] = message['from'].find('/') != -1 and message['from'].split('/')[1] or message['from']
            if event.sender['id'] == self.parent.nick:
                return
            event.sender['nick'] = event.sender['id']
            event.channel = message['from'].split('/')[0]
            event.public = True
        else:
            event.sender['id'] = event.sender['connection'].split('/')[0]
            event.sender['nick'] = event.sender['connection'].split('@')[0]
            event.channel = event.sender['connection']
            event.public = False
            event.addressed = True

        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        message = domish.Element((None, 'message'))
        message['to'] = response['target']
        message['from'] = self.parent.authenticator.jid.full()
        if message['to'] in self.rooms:
            message['type'] = 'groupchat'
        else:
            message['type'] = 'chat'
        message.addElement('body', content=response['reply'])
        self.xmlstream.send(message)
        self.parent.log.debug(u"Sent %s message to %s: %s", message['type'], message['to'], message.body)

    def join(self, room):
        self.parent.log.info(u"Joining %s", room)
        jid = JID('%s/%s' % (room, self.parent.nick))
        presence = xmppim.AvailablePresence(to=jid)
        self.xmlstream.send(presence)
        self.rooms.append(room.lower())

    def leave(self, room):
        self.parent.log.info(u"Leaving %s", room)
        jid = JID('%s/%s' % (room, self.parent.nick))
        presence = xmppim.UnavailablePresence(to=jid)
        self.xmlstream.send(presence)
        self.rooms.remove(room.lower())


class IbidXMPPClientConnector(client.XMPPClientConnector):
    def __init__(self, reactor, domain, factory, server, port, ssl):
        client.XMPPClientConnector.__init__(self, reactor, domain, factory)
        self.overridden_server = server
        self.overridden_port = port
        self.overridden_ssl = ssl

    def pickServer(self):
        srvhost, srvport = client.XMPPClientConnector.pickServer(self)
        host, port = self.overridden_server, self.overridden_port
        if host is None:
            host = srvhost
        if self.overridden_ssl:
            if port is None:
                port = 5223
            self.connectFuncName = 'connectSSL'
            self.connectFuncArgs = [ssl.ClientContextFactory()]
        if port is None:
            port = srvport
        self.factory.log.info(u'Connecting to: %s:%s%s', host, port,
                              self.overridden_ssl and ' using SSL' or '')
        return host, port

    def connectionFailed(self, reason):
        self.factory.log.error(u'Connection failed: %s', reason)
        self.factory.clientConnectionFailed(self, reason)

    def connectionLost(self, reason):
        self.factory.log.error(u'Connection lost: %s', reason)
        self.factory.clientConnectionLost(self, reason)


class SourceFactory(client.DeferredClientFactory,
                    protocol.ReconnectingClientFactory,
                    IbidSourceFactory):
    auth = ('implicit',)
    supports = ('multiline',)

    jid_str = Option('jid', 'Jabber ID')
    server = Option('server', 'Server hostname (defaults to SRV lookup, '
                              'falling back to JID domain)')
    port = IntOption('port', 'Server port number (defaults to SRV lookup, '
                             'falling back to 5222/5223')
    ssl = BoolOption('ssl', 'Use SSL instead of automatic TLS')
    password = Option('password', 'Jabber password')
    nick = Option('nick', 'Nick for chatrooms', ibid.config['botname'])
    rooms = ListOption('rooms', 'Chatrooms to autojoin', [])
    accept_domains = ListOption('accept_domains',
            'Only accept messages from these domains', [])
    max_public_message_length = IntOption('max_public_message_length',
            'Maximum length of public messages', 512)

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        self.log = logging.getLogger('source.%s' % name)
        client.DeferredClientFactory.__init__(self, JID(self.jid_str),
                                              self.password)
        bot = JabberBot()
        self.addHandler(bot)
        bot.setHandlerParent(self)

    def setServiceParent(self, service):
        c = IbidXMPPClientConnector(reactor, self.authenticator.jid.host, self,
                                    self.server, self.port, self.ssl)
        c.connect()

    def connect(self):
        return self.setServiceParent(None)

    def disconnect(self):
        self.stopTrying()
        self.stopFactory()
        self.proto.xmlstream.transport.loseConnection()
        return True

    def join(self, room):
        return self.proto.join(room)

    def leave(self, room):
        return self.proto.leave(room)

    def url(self):
        return u'xmpp://%s' % (self.jid_str,)

    def logging_name(self, identity):
        return identity.split('/')[0]

    def truncation_point(self, response, event=None):
        if response.get('target', None) in self.proto.rooms:
            return self.max_public_message_length
        return None

# vi: set et sta sw=4 ts=4:
