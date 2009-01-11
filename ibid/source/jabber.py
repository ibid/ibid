from wokkel import client, xmppim, subprotocols, compat
from twisted.internet import reactor, protocol, ssl
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish
from twisted.application import internet

import ibid
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
        xmppim.MessageProtocol.connectionInitialized(self)
        xmppim.PresenceClientProtocol.connectionInitialized(self)
        xmppim.RosterClientProtocol.connectionInitialized(self)
        self.xmlstream.send(xmppim.AvailablePresence())
        self.name = self.parent.name
        self.parent.send = self.send
        self.parent.proto = self
        if 'rooms' in ibid.config.sources[self.name]:
            for room in ibid.config.sources[self.name]['rooms']:
                self.join(room)

    def availableReceived(self, entity, show=None, statuses=None, priority=0):
        event = Event(self.name, u'state')
        event.sender = entity.full()
        event.sender_id = event.sender.split('/')[0]
        event.who = event.sender.split('@')[0]
        event.state = show or u'available'
        event.channel = entity.full()
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def unavailableReceived(self, entity, statuses):
        event = Event(self.name, u'state')
        event.sender = entity.full()
        event.sender_id = event.sender.split('/')[0]
        event.who = event.sender.split('@')[0]
        event.state = u'offline'
        event.channel = entity.full()
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def subscribeReceived(self, entity):
        print "Accepting subscription request from " + entity.full()
        response = xmppim.Presence(to=entity, type='subscribed')
        self.xmlstream.send(response)
        response = xmppim.Presence(to=entity, type='subscribe')
        self.xmlstream.send(response)

    def onMessage(self, message):
        if message.x and message.x.defaultUri == 'jabber:x:delay':
            return

        event = Event(self.parent.name, u'message')
        event.message = unicode(message.body)
        event.sender = unicode(message['from'])

        if message['type'] == 'groupchat':
            event.sender_id = message['from'].split('/')[1]
            if event.sender_id == ibid.config.sources[self.name]['nick']:
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
        message['from'] = self.parent.jid.full()
        if message['to'] in self.rooms:
            message['type'] = 'groupchat'
        else:
            message['type'] = 'chat'
        message.addElement('body', content=response['reply'])
        self.xmlstream.send(message)

    def join(self, room):
        jid = JID('%s/%s' % (room, ibid.config.sources[self.name]['nick']))
        presence = xmppim.AvailablePresence(to=jid)
        self.xmlstream.send(presence)
        self.rooms.append(room)

    def part(self, room):
        jid = JID('%s/%s' % (room, ibid.config.sources[self.name]['nick']))
        presence = xmppim.UnavailablePresence(to=jid)
        self.xmlstream.send(presence)
        self.rooms.remove(room)

class SourceFactory(client.DeferredClientFactory, IbidSourceFactory):

    def __init__(self, name):
        client.DeferredClientFactory.__init__(self, JID(ibid.config.sources[name]['jid']), ibid.config.sources[name]['password'])
        IbidSourceFactory.__init__(self, name)
        bot = JabberBot()
        self.addHandler(bot)
        bot.setHandlerParent(self)

    def setServiceParent(self, service):
        port = None
        server = ibid.config.sources[self.name]['server']

        if 'port' in ibid.config.sources[self.name]:
            port = ibid.config.sources[self.name]['port']

        if 'ssl' in ibid.config.sources[self.name] and ibid.config.sources[self.name]['ssl']:
            sslctx = ssl.ClientContextFactory()
            port = port or 5223
            if service:
                internet.SSLClient(server, port, self, sslctx).setServiceParent(service)
            else:
                reactor.connectSSL(server, port, self, sslctx)
        else:
            port = port or 5222
            if service:
                internet.TCPClient(server, port, self).setServiceParent(service)
            else:
                reactor.connectTCP(server, port, self)

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
