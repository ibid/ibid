#!/usr/bin/python

from twisted.internet import reactor, threads

from twisted.words.protocols import irc
from twisted.internet import protocol

import re, time

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

		self.factory.processor.process(message, self.dispatch)

	def dispatch(self, query):
		for response in query['responses']:
			self.msg(response['target'], response['reply'])

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
