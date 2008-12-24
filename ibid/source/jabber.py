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

class JabberBot(xmppim.MessageProtocol, xmppim.PresenceClientProtocol):

    def __init__(self):
        xmppim.MessageProtocol.__init__(self)

    def connectionInitialized(self):
        xmppim.MessageProtocol.connectionInitialized(self)
        xmppim.PresenceClientProtocol.connectionInitialized(self)
        self.xmlstream.send(xmppim.AvailablePresence())
        self.name = self.parent.name
        self.parent.respond = self.respond
        self.parent.proto = self

    def availableReceived(self, entity, show=None, statuses=None, priority=0):
        event = Event(self.name, 'state')
        event.user = entity.full()
        event.state = show or 'available'
        event.channel = entity.full()
        ibid.dispatcher.dispatch(event)

    def subscribeReceived(self, entity):
        print "Accepting subscription request from " + entity.full()
        response = xmppim.Presence(to=entity, type='subscribed')
        self.xmlstream.send(response)
        response = xmppim.Presence(to=entity, type='subscribe')
        self.xmlstream.send(response)

    def onMessage(self, message):
        event = Event(self.parent.name, 'message')
        event.message = str(message.body)
        event.user = message['from']
        event.channel = message['from']
        event.public = False
        event.addressed = True
        ibid.dispatcher.dispatch(event)

    def respond(self, response):
        print response
        message = domish.Element((None, 'message'))
        message['to'] = response['target']
        message['from'] = 'ibid@gorven.za.net'
        message['type'] = 'chat'
        message.addElement('body', content=response['reply'])
        self.xmlstream.send(message)

class SourceFactory(client.DeferredClientFactory, IbidSourceFactory):

    def __init__(self, name):
        client.DeferredClientFactory.__init__(self, JID(ibid.config.sources[name]['jid']), ibid.config.sources[name]['password'])
        bot = JabberBot()
        self.addHandler(bot)
        bot.setHandlerParent(self)

        self.name = name
        self.respond = None

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

# vi: set et sta sw=4 ts=4:
