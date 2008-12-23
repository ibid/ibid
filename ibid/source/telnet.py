from twisted.internet import protocol, reactor
from twisted.protocols import basic
from twisted.application import internet

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

encoding = 'latin-1'

class TelnetProtocol(basic.LineReceiver):

    def connectionMade(self):
        self.factory.respond = self.respond

    def lineReceived(self, line):

        event = Event(self.factory.name, 'message')
        event.message = line
        event.user = 'telnet'
        event.channel = 'telnet'
        event.addressed = True
        event.public = False
        ibid.dispatcher.dispatch(event)

    def respond(self, response):
        self.sendLine(response['reply'].encode(encoding))

class SourceFactory(protocol.ServerFactory, IbidSourceFactory):
    protocol = TelnetProtocol

    def setServiceParent(self, service=None):
        port = 3000
        if 'port' in ibid.config.sources[self.name]:
            port = ibid.config.sources[self.name]['port']

        if service:
            return internet.TCPServer(port, self).setServiceParent(service)
        else:
            reactor.listenTCP(port, self)

    def connect(self):
        return self.setServiceParent(None)

# vi: set et sta sw=4 ts=4:
