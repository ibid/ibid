from wokkel import client, xmppim, subprotocols, compat
from twisted.internet import reactor, protocol
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish

import ibid

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
		self.name = self.parent.config['name']
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
		event = {	'source': self.parent.config['name'],
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

class SourceFactory(client.DeferredClientFactory):

	def __init__(self, config):
		client.DeferredClientFactory.__init__(self, JID(config['jid']), config['password'])
		bot = JabberBot()
		self.addHandler(bot)
		bot.setHandlerParent(self)
		self.config = config
		self.respond = None
