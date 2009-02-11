import logging

from wokkel import client, xmppim
from twisted.internet import reactor, ssl
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish
from twisted.application import internet

import ibid
from ibid.config import Option, IntOption, BoolOption
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
        self.name = self.parent.name
        self.parent.send = self.send
        self.parent.proto = self
        for room in self.parent.rooms:
            self.join(room)

    def availableReceived(self, entity, show=None, statuses=None, priority=0):
        event = Event(self.name, u'state')
        event.sender = entity.full()
        event.sender_id = event.sender.split('/')[0]
        event.who = event.sender.split('@')[0]
        event.state = show or u'online'
        event.channel = entity.full()
        self.parent.log.debug(u"Received available presence from %s (%s)", event.sender, event.state)
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def unavailableReceived(self, entity, statuses):
        event = Event(self.name, u'state')
        event.sender = entity.full()
        event.sender_id = event.sender.split('/')[0]
        event.who = event.sender.split('@')[0]
        event.state = u'offline'
        event.channel = entity.full()
        self.parent.log.debug(u"Received unavailable presence from %s", event.sender)
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

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

        event = Event(self.parent.name, u'message')
        event.message = unicode(message.body)
        event.sender = message['from']

        if message['type'] == 'groupchat':
            event.sender_id = message['from'].find('/') != -1 and message['from'].split('/')[1] or message['from']
            if event.sender_id == self.parent.nick:
                return
            event.who = event.sender_id
            event.channel = message['from'].split('/')[0]
            event.public = True
        else:
            event.sender_id = event.sender.split('/')[0]
            event.who = event.sender.split('@')[0]
            event.channel = event.sender
            event.public = False
            event.addressed = True

        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        message = domish.Element((None, 'message'))
        message['to'] = response['target']
        message['from'] = self.parent.jid_str
        if message['to'] in self.rooms:
            message['type'] = 'groupchat'
        else:
            message['type'] = 'chat'
        message.addElement('body', content=response['reply'])
        self.xmlstream.send(message)
        self.parent.log.debug(u"Sent %s message to %s: %s", message['type'], message['to'], message.body)

    def join(self, room):
        jid = JID('%s/%s' % (room, self.parent.nick))
        presence = xmppim.AvailablePresence(to=jid)
        self.xmlstream.send(presence)
        self.rooms.append(room)
        self.parent.log.info(u"Joining %s", room)

    def part(self, room):
        jid = JID('%s/%s' % (room, self.parent.nick))
        presence = xmppim.UnavailablePresence(to=jid)
        self.xmlstream.send(presence)
        self.rooms.remove(room)
        self.parent.log.info(u"Leaving %s", room)

class SourceFactory(client.DeferredClientFactory, IbidSourceFactory):

    port = IntOption('port', 'Server port number')
    ssl = BoolOption('ssl', 'Usel SSL', False)
    server = Option('server', 'Server hostname')
    jid_str = Option('jid', 'Jabber ID')
    password = Option('password', 'Jabber password')
    nick = Option('nick', 'Nick for chatrooms', ibid.config['botname'])
    rooms = Option('rooms', 'Chatrooms to autojoin', [])
    accept_domains = Option('accept_domains', 'Only accept messages from these domains')

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        self.log = logging.getLogger('source.%s' % name)
        client.DeferredClientFactory.__init__(self, JID(self.jid_str), self.password)
        bot = JabberBot()
        self.addHandler(bot)
        bot.setHandlerParent(self)

    def setServiceParent(self, service):
        if self.ssl:
            sslctx = ssl.ClientContextFactory()
            port = self.port or 5223
            if service:
                internet.SSLClient(self.server, port, self, sslctx).setServiceParent(service)
            else:
                reactor.connectSSL(self.server, port, self, sslctx)
        else:
            port = self.port or 5222
            if service:
                internet.TCPClient(self.server, port, self).setServiceParent(service)
            else:
                reactor.connectTCP(self.server, port, self)

    def connect(self):
        return self.setServiceParent(None)

    def disconnect(self):
        self.stopFactory()
        self.proto.xmlstream.transport.loseConnection()
        return True

    def join(self, room):
        return self.proto.join(room)

    def part(self, room):
        return self.proto.part(room)

# vi: set et sta sw=4 ts=4:
