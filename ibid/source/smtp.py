from StringIO import StringIO

from twisted.application import internet
from twisted.internet import protocol
from twisted.mail import smtp

import ibid
from ibid.source import IbidSourceFactory

class SMTPClient(smtp.ESMTPClient):

    mailFrom = 'test@example.com'
    mailTo = ['mgorven@localhost']
    headers = {'Subject': 'Testing'}
    message = 'Just testing!'

    def getMailFrom(self):
        return self.mailFrom

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
        print code
        print resp
        print numOk
        print addresses
        print log
        self.transport.loseConnection()

class SMTPClientFactory(protocol.ClientFactory):
    protocol = SMTPClient

    def buildProtocol(self, addr):
        return self.protocol(secret=None, identity='example.com')

class SourceFactory(IbidSourceFactory):

    def setServiceParent(self, service):
        self.service = service

    def send(self, event):
        factory = SMTPClientFactory()
        internet.TCPClient(ibid.config.sources[self.name]['relayhost'], 25, factory).setServiceParent(self.service)

# vi: set et sta sw=4 ts=4:
