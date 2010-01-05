import logging
from datetime import datetime
from email import message_from_string
from socket import gethostname
import re

from twisted.application import internet
from twisted.internet import defer, reactor
from twisted.mail import smtp
from zope.interface import implements

import ibid
from ibid.compat import email_utils
from ibid.config import Option, IntOption, ListOption
from ibid.event import Event
from ibid.source import IbidSourceFactory

stripsig = re.compile(r'^-- $.*', re.M+re.S)

class IbidDelivery:
    implements(smtp.IMessageDelivery)

    def __init__(self, factory):
        self.factory = factory

    def receivedHeader(self, helo, origin, recipients):
        return 'Received: from %s ([%s])\n\tby %s (Ibid)\n\tfor %s; %s' % (
            helo[0], helo[1], gethostname(), str(recipients[0]),
            datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000 (UTC)')
        )

    def validateFrom(self, helo, origin):
        return origin

    def validateTo(self, user):
        if str(user) == self.factory.address or str(user) in self.factory.accept:
            return lambda: Message(self.factory.name)
        raise smtp.SMTPBadRcpt(user)

class Message:
    implements(smtp.IMessage)

    def __init__(self, name):
        self.lines = []
        self.name = name
        self.log = logging.getLogger('source.%s' % name)

    def lineReceived(self, line):
        self.lines.append(line)

    def eomReceived(self):
        mail = message_from_string('\n'.join(self.lines))

        event = Event(self.name, u'message')
        (realname, address) = email_utils.parseaddr(mail['from'])
        event.channel = event.sender['connection'] = event.sender['id'] = unicode(address, 'utf-8', 'replace')
        event.sender['nick'] = realname != '' and unicode(realname, 'utf-8', 'replace') or event.channel
        event.public = False
        event.addressed = True
        event.subject = unicode(mail['subject'], 'utf-8', 'replace')
        event.headers = dict((i[0], unicode(i[1], 'utf-8', 'replace')) for i in mail.items())

        message = mail.is_multipart() and mail.get_payload()[0].get_payload() or mail.get_payload()
        if len(message) > 0:
            event.message = stripsig.sub('', (message, 'utf-8', 'replace')).strip().replace('\n', ' ')
        else:
            event.message = event.subject

        self.log.debug(u"Received message from %s: %s", event.sender['connection'], event.message)
        ibid.dispatcher.dispatch(event).addCallback(ibid.sources[self.name.lower()].respond)
        return defer.succeed(None)

    def connectionLost(self):
        self.lines = None

class SourceFactory(IbidSourceFactory, smtp.SMTPFactory):

    supports = ('multiline',)

    port = IntOption('port', 'Port number to listen on', 10025)
    address = Option('address', 'Email address to accept messages for and send from', 'ibid@localhost')
    accept = ListOption('accept', 'Email addresses to accept messages for', [])
    relayhost = Option('relayhost', 'SMTP server to relay outgoing messages to')

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        self.log = logging.getLogger('source.%s' % name)
        self.delivery = IbidDelivery(self)

    def buildProtocol(self, addr):
        p = smtp.SMTPFactory.buildProtocol(self, addr)
        p.delivery = self.delivery
        return p

    def setServiceParent(self, service):
        self.service = service
        if service:
            internet.TCPServer(self.port, self).setServiceParent(service)
        else:
            reactor.listenTCP(self.port, self)

    def url(self):
        return u'mailto:%s' % (self.address,)

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
        response['to'] = response['target']
        response['date'] = smtp.rfc822date()
        if 'subject' not in response:
            response['subject'] = 'Message from %s' % ibid.config['botname']

        del response['target']
        del response['source']
        del response['reply']

        body = ''
        for header, value in response.items():
            body += '%s: %s\n' % (header, value)
        body += '\n'
        body += message

        smtp.sendmail(self.relayhost, self.address, response['to'], body.encode('utf-8'))
        self.log.debug(u"Sent email to %s: %s", response['to'], response['subject'])

# vi: set et sta sw=4 ts=4:
