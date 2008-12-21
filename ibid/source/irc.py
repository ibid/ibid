import re

from twisted.internet import reactor
from twisted.words.protocols import irc
from twisted.internet import protocol

encoding = 'latin-1'

class Ircbot(irc.IRCClient):
        
	def connectionMade(self):
		self.nickname = self.factory.nick
		irc.IRCClient.connectionMade(self)

	def connectionLost(self, reason):
		irc.IRCClient.connectionLost(self, reason)

	def signedOn(self):
		for z in self.factory.channels:
			self.join(z)

	def privmsg(self, user, channel, msg):
		user = user.split('!', 1)[0]
		message = {"msg":msg, "user":user, "channel":channel}

		newmsg = re.sub(r"^\s*%s([:;.?>!,-]+)*\s+" % self.nickname,"",msg)
		if newmsg != msg:
			message["addressed"] = True
			message["msg"] = newmsg
		else:
			message["addressed"] = False
		if channel.lower() == self.nickname.lower():
			message["addressed"] = True
			message["public"] = False
			message["channel"] = user
		else:
			message["public"] = True

		message['responses'] = []
		message['processed'] = False
		self.factory.processor.process(message, self.dispatch)

	def dispatch(self, query):
		print query
		for response in query['responses']:
			if isinstance(response, basestring):
				response = {'reply': response}

			target = 'target' in response and response['target'] or query['channel']
			if 'action' in response and response['action']:
				self.me(target, response['reply'].encode(encoding))
			else:
				self.msg(target, response['reply'].encode(encoding))

class SourceFactory(protocol.ClientFactory):
	protocol = Ircbot

	def __init__(self, processor, nick, channels):
		self.processor = processor
		self.nick = nick
		self.channels = channels

	def clientConnectionLost(self, connector, reason):
		"""If we get disconnected, reconnect to server."""
		connector.connect()

	def clientConnectionFailed(self, connector, reason):
		print "connection failed:", reason
		reactor.stop()
