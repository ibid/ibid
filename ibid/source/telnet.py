import logging

from twisted.internet import protocol, reactor
from twisted.conch import telnet
from twisted.application import internet

import ibid
from ibid.source import IbidSourceFactory
from ibid.config import IntOption
from ibid.event import Event
from ibid.config import IntOption

class TelnetProtocol(telnet.StatefulTelnetProtocol):

    state = 'User'

    def connectionMade(self):
        self.factory.send = self.send
        self.transport.write('Username: ')

    def telnet_User(self, line):
        self.user = unicode(line.strip(), 'utf-8', 'replace')
        if ' ' in self.user:
            self.transport.write('Sorry, no spaces allowed in usernames\r\n')
            self.factory.log.info(u"Rejected connection from %s", self.user)
            self.transport.loseConnection()
            return

        self.factory.log.info(u"Connection established with %s", self.user)
        return 'Query'

    def telnet_Query(self, line):
        event = Event(self.factory.name, u'message')
        event.message = unicode(line.strip(), 'utf-8', 'replace')
        event.sender['connection'] = self.user
        event.sender['id'] = self.user
        event.sender['nick'] = event.sender['connection']
        event.channel = event.sender['connection']
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

    port = IntOption('port', 'Port to listen on', 3000)

    def __init__(self, name, *args, **kwargs):
        #protocol.ServerFactory.__init__(self, *args, **kwargs)
        IbidSourceFactory.__init__(self, name)
        self.log = logging.getLogger('source.%s' % name)

    def setServiceParent(self, service=None):
        if service:
            self.listener = internet.TCPServer(self.port, self).setServiceParent(service)
            return self.listener
        else:
            self.listener = reactor.listenTCP(self.port, self)

    def connect(self):
        return self.setServiceParent(None)

    def disconnect(self):
        self.listener.stopListening()
        return True

# vi: set et sta sw=4 ts=4:
