from StringIO import StringIO

from twisted.application import internet
from twisted.internet import protocol, defer
from twisted.mail import smtp
from zope.interface import implements

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

class SMTPClient(smtp.ESMTPClient):

    def getMailFrom(self):
        value = self.mailFrom
        self.mailFrom = None
        return value

    def getMailTo(self):
        return self.mailTo

    def getMailData(self):
        body = ''
        for header, value in self.headers.items():
            body += '%s: %s\n' % (header, value)
        body += '\n'
        body += self.message
        return StringIO(body)

    def sentMail(self, code, resp, numOk, addresses, log):
        pass

class SMTPClientFactory(protocol.ClientFactory):
    protocol = SMTPClient

    def __init__(self, name, response):
        self.response = response
        self.name = name

    def buildProtocol(self, addr):
        client = self.protocol(secret=None, identity='localhost')
        client.mailFrom = ibid.config.sources[self.name]['from']
        client.mailTo = [self.response['target']]
        client.message = self.response['reply']

        self.response['To'] = self.response['target']
        self.response['Date'] = smtp.rfc822date()
        del self.response['target']
        del self.response['source']
        del self.response['reply']
        client.headers = self.response

        return client

class IbidDelivery:
    implements(smtp.IMessageDelivery)

    def __init__(self, name):
        self.name = name

    def receivedHeader(self, helo, origin, recipients):
        return 'Received: by Ibid'

    def validateFrom(self, helo, origin):
        return origin

    def validateTo(self, user):
        if str(user) == 'ibid@localhost':
            return lambda: Message(self.name)
        raise smtp.SMTPBadRcpt(user)

class Message:
    implements(smtp.IMessage)

    def __init__(self, name):
        self.lines = []
        self.name = name

    def lineReceived(self, line):
        self.lines.append(line)

    def eomReceived(self):
        headers = {}
        for line in self.lines:
            if line == '':
                break
            (header, value) = line.split(':')
            headers[header.strip().lower()] = value.strip()

        event = Event(self.name, 'message')
        event.sender = headers['from']
        event.sender_id = event.sender
        event.who = event.sender
        event.channel = event.sender
        event.public = False
        event.addressed = True
        event.message = headers['subject']

        ibid.dispatcher.dispatch(event)
        return defer.succeed(None)

    def connectionLost(self):
        self.lines = None

class SourceFactory(IbidSourceFactory, smtp.SMTPFactory):

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        self.delivery = IbidDelivery(name)

    def buildProtocol(self, addr):
        p = smtp.SMTPFactory.buildProtocol(self, addr)
        p.delivery = self.delivery
        return p

    def setServiceParent(self, service):
        self.service = service
        internet.TCPServer(10025, self).setServiceParent(service)

    def send(self, response):
        factory = SMTPClientFactory(self.name, response)
        
        internet.TCPClient(ibid.config.sources[self.name]['relayhost'], 25, factory).setServiceParent(self.service)

# vi: set et sta sw=4 ts=4:
