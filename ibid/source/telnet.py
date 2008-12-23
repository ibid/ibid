from twisted.internet import protocol, reactor
from twisted.protocols import basic
from twisted.application import internet

import ibid
from ibid.source import IbidSourceFactory

encoding = 'latin-1'

class TelnetProtocol(basic.LineReceiver):

	def connectionMade(self):
		self.factory.respond = self.respond

	def lineReceived(self, line):

		event =	{	'source': self.factory.name,
					'msg': line,
					'user': 'telnet',
					'channel': 'telnet',
					'addressed': True,
					'public': False,
				}
		ibid.core.dispatcher.dispatch(event)

	def respond(self, response):
		self.sendLine(response['reply'].encode(encoding))

class SourceFactory(protocol.ServerFactory, IbidSourceFactory):
	protocol = TelnetProtocol

	def setServiceParent(self, service=None):
		port = 3000
		if 'port' in ibid.core.config['sources'][self.name]:
			port = ibid.core.config['sources'][self.name]['port']

		if service:
			return internet.TCPServer(port, self).setServiceParent(service)
		else:
			reactor.listenTCP(port, self)

	def connect(self):
		return self.setServiceParent(None)
