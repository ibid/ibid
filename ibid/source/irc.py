import re

from twisted.internet import reactor
from twisted.words.protocols import irc
from twisted.internet import protocol

encoding = 'latin-1'

class Ircbot(irc.IRCClient):
        
	def connectionMade(self):
		self.nickname = self.factory.nick
		irc.IRCClient.connectionMade(self)
		self.factory.resetDelay()

	def connectionLost(self, reason):
		irc.IRCClient.connectionLost(self, reason)

	def signedOn(self):
		for z in self.factory.channels:
			self.join(z)

	def privmsg(self, user, channel, msg):
		user = user.split('!', 1)[0]
		message = {"msg":msg, "user":user, "channel":channel}

		if channel.lower() == self.nickname.lower():
			message["addressed"] = True
			message["public"] = False
			message["channel"] = user
		else:
			message["public"] = True

		message['source'] = self.factory.name
		message['responses'] = []
		message['processed'] = False
		self.factory.processor.process(message, self.dispatch)

	def dispatch(self, query):
		print query
		for response in query['responses']:
			if 'action' in response and response['action']:
				self.me(response['target'], response['reply'].encode(encoding))
			else:
				self.msg(response['target'], response['reply'].encode(encoding))

class SourceFactory(protocol.ReconnectingClientFactory):
	protocol = Ircbot

	def __init__(self, processor, name, nick, channels):
		self.processor = processor
		self.name = name
		self.nick = nick
		self.channels = channels
