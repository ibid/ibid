from twisted.internet import protocol, reactor
from twisted.conch import telnet
from twisted.application import internet

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

encoding = 'utf-8'

class TelnetProtocol(telnet.StatefulTelnetProtocol):

    state = 'User'

    def connectionMade(self):
        self.factory.send = self.send
        self.transport.write('Username: ')

    def telnet_User(self, line):
        self.user = line.strip()
        return 'Query'

    def telnet_Query(self, line):
        event = Event(self.factory.name, 'message')
        event.message = line.strip()
        event.sender = self.user
        event.sender_id = self.user
        event.who = event.sender
        event.channel = event.sender
        event.addressed = True
        event.public = False
        ibid.dispatcher.dispatch(event).addCallback(self.respond)
        return 'Query'

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        self.transport.write(response['reply'].encode(encoding) + '\n')

class SourceFactory(protocol.ServerFactory, IbidSourceFactory):
    protocol = TelnetProtocol

    port = 3000

    def setServiceParent(self, service=None):
        if service:
            return internet.TCPServer(self.port, self).setServiceParent(service)
        else:
            reactor.listenTCP(self.port, self)

    def connect(self):
        return self.setServiceParent(None)

# vi: set et sta sw=4 ts=4:
