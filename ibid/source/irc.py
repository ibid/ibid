import re

from twisted.internet import reactor
from twisted.words.protocols import irc
from twisted.internet import protocol

encoding = 'latin-1'

class Ircbot(irc.IRCClient):
        
	def connectionMade(self):
		self.nickname = self.factory.config['nick']
		irc.IRCClient.connectionMade(self)
		self.factory.resetDelay()
		self.factory.respond = self.respond

	def connectionLost(self, reason):
		irc.IRCClient.connectionLost(self, reason)

	def signedOn(self):
		for channel in self.factory.config['channels']:
			self.join(channel)

	def privmsg(self, user, channel, msg):
		user = user.split('!', 1)[0]
		message = {"msg":msg, "user":user, "channel":channel}

		if channel.lower() == self.nickname.lower():
			message["addressed"] = True
			message["public"] = False
			message["channel"] = user
		else:
			message["public"] = True

		message['source'] = self.factory.config['name']
		message['responses'] = []
		message['processed'] = False
		self.factory.processor.process(message)

	def respond(self, response):
		if 'action' in response and response['action']:
			self.me(response['target'], response['reply'].encode(encoding))
		else:
			self.msg(response['target'], response['reply'].encode(encoding))

		if 'ircaction' in response:
			(action, channel) = response['ircaction']
			if action == 'join':
				self.join(channel)
			elif action == 'part':
				self.part(channel)

class SourceFactory(protocol.ReconnectingClientFactory):
	protocol = Ircbot

	def __init__(self, processor, config):
		self.processor = processor
		self.config = config
		self.respond = None
