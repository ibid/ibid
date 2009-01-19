import logging

from twisted.internet import protocol, reactor
from twisted.conch import telnet
from twisted.application import internet

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

class TelnetProtocol(telnet.StatefulTelnetProtocol):

    state = 'User'

    def connectionMade(self):
        self.factory.send = self.send
        self.transport.write('Username: ')

    def telnet_User(self, line):
        self.user = unicode(line.strip(), 'utf-8', 'replace')
        self.factory.log.info(u"Connection established with %s", self.user)
        return 'Query'

    def telnet_Query(self, line):
        event = Event(self.factory.name, u'message')
        event.message = unicode(line.strip(), 'utf-8', 'replace')
        event.sender = self.user
        event.sender_id = self.user
        event.who = event.sender
        event.channel = event.sender
        event.addressed = True
        event.public = False
        self.factory.log.debug(u"Received message from %s: %s", self.user, event.message)
        ibid.dispatcher.dispatch(event).addCallback(self.respond)
        return 'Query'

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        self.transport.write(response['reply'].encode('utf-8') + '\n')
        self.factory.log.debug(u"Sent message to %s: %s", self.user, response['reply'])

class SourceFactory(protocol.ServerFactory, IbidSourceFactory):
    protocol = TelnetProtocol

    port = 3000

    def __init__(self, name, *args, **kwargs):
        #protocol.ServerFactory.__init__(self, *args, **kwargs)
        IbidSourceFactory.__init__(self, name)
        self.log = logging.getLogger('source.%s' % name)

    def setServiceParent(self, service=None):
        if service:
            return internet.TCPServer(self.port, self).setServiceParent(service)
        else:
            reactor.listenTCP(self.port, self)

    def connect(self):
        return self.setServiceParent(None)

# vi: set et sta sw=4 ts=4:
