#!/usr/bin/python

from twisted.internet import glib2reactor
glib2reactor.install()
from twisted.internet import reactor

from twisted.words.protocols import irc
from twisted.internet import protocol

import dbus
import dbus.service
import dbus.mainloop.glib

import re, time

class IrcbotDBus(dbus.service.Object):
    def __init__(self, conn, object_path='/com/example/TestService/object'):
        dbus.service.Object.__init__(self, conn, object_path)

    @dbus.service.signal(dbus_interface='com.example.Sample', signature='ssas')
    def IRCEvent(self, type, target, params):
        print "XXX %s, %s, %s" % (type, target, params)

class Ircbot(irc.IRCClient):
	def __init__(self):
	    self.responses = [
			(r"\s*(say|do)\s+(\S+)\s+(.*)", self.h_saydo),
			(r"\s*(?:time|date)", self.h_datetime),
			(r"\s*(join|leave)\s+(#\S*)", self.h_joinleave),
		]
            self.dbus = IrcbotDBus(dbus.SessionBus())    
        
        def handleCommand(self, command, prefix, params):
            #print "%s, %s, %s" % (command, prefix, params)
            self.dbus.IRCEvent(command, prefix, params)
            return irc.IRCClient.handleCommand(self, command, prefix, params)

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
			message["addressed"] = 1
			message["msg"] = newmsg
		else:
			message["addressed"] = 0
		if channel.lower() == self.nickname.lower():
			message["addressed"] = 1
			message["public"] = 0
			message["channel"] = user
		else:
			message["public"] = 1

		if not message["addressed"]:
			return
		for regex, handler in self.responses:
			m = re.match(regex, message["msg"], re.IGNORECASE)
			if m:
				handler(message,*m.groups())

	def h_saydo(self, msg, action, where, what):
		if(msg["user"] != "Vhata"):
			self.msg(msg["channel"],"No!  You're not the boss of me!")
			if action.lower() == "say":
				self.msg(where,"Ooooh! %s was trying to make me say '%s'!" % (m["user"], what))
			else:
				self.me(where,"refuses to do '%s' for '%s'" % (what, m["user"]))
		else:
			if action.lower() == "say":
				self.msg(where,what)
			else:
				self.me(where,what)

	def h_datetime(self, msg):
		if msg["channel"] == msg["user"]: addr = ""
		else: addr = msg["user"]+": "
		self.msg(msg["channel"],addr+time.strftime("It is %H:%M.%S on %a, %e %b %Y",time.localtime()))

	def h_joinleave(self, msg, action, chan):
		if action.lower() == "join":
			self.msg(msg["channel"], "Joining %s" % chan)
			self.join(chan)
		else:
			self.msg(msg["channel"], "Fine, I know where I'm not wanted")
			self.part(chan)

class IrcbotFactory(protocol.ClientFactory):
	protocol = Ircbot

	def __init__(self, nick, channels):
		self.nick = nick
		self.channels = channels

	def clientConnectionLost(self, connector, reason):
		"""If we get disconnected, reconnect to server."""
		connector.connect()

	def clientConnectionFailed(self, connector, reason):
		print "connection failed:", reason
		reactor.stop()

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
f = IrcbotFactory("Lettuce", ["#", "#family"])
reactor.connectTCP("irc.atrum.org", 6667, f)
reactor.run()
