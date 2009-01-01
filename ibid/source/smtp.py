from StringIO import StringIO

from twisted.application import internet
from twisted.internet import protocol, defer
from twisted.mail import smtp
from zope.interface import implements

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

class IbidDelivery:
    implements(smtp.IMessageDelivery)

    def __init__(self, name):
        self.name = name

    def receivedHeader(self, helo, origin, recipients):
        return 'Received: by Ibid'

    def validateFrom(self, helo, origin):
        return origin

    def validateTo(self, user):
        if str(user) == ibid.config.sources[self.name]['address']:
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
        message = []
        inmessage = False
        for line in self.lines:
            if inmessage:
                if line == '-- ':
                    break
                elif line != '':
                    message.append(line)
            else:
                if line == '':
                    inmessage = True
                elif line.startswith('  '):
                    headers[last] += line
                else:
                    (header, value) = line.split(':', 1)
                    last = header.strip().lower()
                    headers[last] = value.strip()

        event = Event(self.name, 'message')
        event.sender = headers['from']
        event.sender_id = event.sender
        event.who = event.sender
        event.channel = event.sender
        event.public = False
        event.addressed = True
        event.subject = headers['subject']
        if len(message) > 0:
            event.message = ' '.join(message)
        else:
            event.message = event.subject

        ibid.dispatcher.dispatch(event).addCallback(ibid.sources[self.name.lower()].respond)
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

    def respond(self, event):
        messages = {}
        for response in event.responses:
            if response['target'] not in messages:
                messages[response['target']] = response
            else:
                messages[response['target']]['reply'] += '\n' + response['reply']

        for message in messages.values():
            if 'subject' not in message:
                message['subject'] = 'Re: ' + event['subject']
            self.send(message)

    def send(self, response):
        message = response['reply']
        response['To'] = response['target']
        response['Date'] = smtp.rfc822date()

        del response['target']
        del response['source']
        del response['reply']

        body = ''
        for header, value in response.items():
            body += '%s: %s\n' % (header, value)
        body += '\n'
        body += message

        smtp.sendmail(ibid.config.sources[self.name]['relayhost'], ibid.config.sources[self.name]['address'], response['To'], body)

# vi: set et sta sw=4 ts=4:
