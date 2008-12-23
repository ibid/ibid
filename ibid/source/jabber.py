from wokkel import client, xmppim, subprotocols, compat
from twisted.internet import reactor, protocol, ssl
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish
from twisted.application import internet

import ibid
from ibid.source import IbidSourceFactory

class Message(domish.Element):
	
	def __init__(self, to, frm, body, type):
		domish.Element(self, (None, 'message'))
		self['to'] = to
		self['from'] = frm
		self['type'] = 'chat'
		self.addElement('body', content=body)

class JabberBot(xmppim.MessageProtocol, xmppim.PresenceClientProtocol):

	def __init__(self):
		xmppim.MessageProtocol.__init__(self)

	def connectionInitialized(self):
		xmppim.MessageProtocol.connectionInitialized(self)
		xmppim.PresenceClientProtocol.connectionInitialized(self)
		self.xmlstream.send(xmppim.AvailablePresence())
		self.name = self.parent.name
		self.parent.respond = self.respond

	def availableReceived(self, entity, show=None, statuses=None, priority=0):
		event =	{	'source': self.name,
					'user': entity.full(),
					'state': show or 'available',
					'channel': entity.full(),
					'responses': [],
					'public': False,
					'addressed': False,
				}
		ibid.core.dispatcher.dispatch(event)

	def subscribeReceived(self, entity):
		print "Accepting subscription request from " + entity.full()
		response = xmppim.Presence(to=entity, type='subscribed')
		self.xmlstream.send(response)
		response = xmppim.Presence(to=entity, type='subscribe')
		self.xmlstream.send(response)

	def onMessage(self, message):
		print message.body
		event = {	'source': self.parent.name,
					'msg': str(message.body),
					'user': message['from'],
					'channel': message['from'],
					'public': False,
					'addressed': True,
					'processed': False,
					'responses': [],
				}
		ibid.core.dispatcher.dispatch(event)

	def respond(self, response):
		print response
		message = domish.Element((None, 'message'))
		message['to'] = response['target']
		message['from'] = 'ibid@gorven.za.net'
		message['type'] = 'chat'
		message.addElement('body', content=response['reply'])
		self.xmlstream.send(message)

class SourceFactory(client.DeferredClientFactory, IbidSourceFactory):

	def __init__(self, name):
		client.DeferredClientFactory.__init__(self, JID(ibid.core.config['sources'][name]['jid']), ibid.core.config['sources'][name]['password'])
		bot = JabberBot()
		self.addHandler(bot)
		bot.setHandlerParent(self)

		self.name = name
		self.respond = None

	def setServiceParent(self, service):
		port = None
		server = ibid.core.config['sources'][self.name]['server']

		if 'port' in ibid.core.config['sources'][self.name]:
			port = ibid.core.config['sources'][self.name]['port']

		if 'ssl' in ibid.core.config['sources'][self.name] and ibid.core.config['sources'][self.name]['ssl']:
			sslctx = ssl.ClientContextFactory()
			port = port or 5223
			if service:
				internet.SSLClient(server, port, self, sslctx).setServiceParent(service)
			else:
				reactor.connectSSL(server, port, self, sslctx)
		else:
			port = port or 5222
			if service:
				internet.TCPClient(server, port, self).setServiceParent(service)
			else:
				reactor.connectTCP(server, port, self)

	def connect(self):
		return self.setServiceParent(None)
