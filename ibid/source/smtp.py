from StringIO import StringIO

from twisted.application import internet
from twisted.internet import protocol
from twisted.mail import smtp

import ibid
from ibid.source import IbidSourceFactory

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

class SourceFactory(IbidSourceFactory):

    def setServiceParent(self, service):
        self.service = service

    def send(self, response):
        factory = SMTPClientFactory(self.name, response)
        
        internet.TCPClient(ibid.config.sources[self.name]['relayhost'], 25, factory).setServiceParent(self.service)

# vi: set et sta sw=4 ts=4:
