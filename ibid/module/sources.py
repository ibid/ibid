import ibid
from ibid.module import Module
from ibid.decorators import *

class Connect(Module):

	@addressed
	@notprocessed
	@match('^\s*(connect)\s+(?:to\s+)?(\S+)\s*$')
	def process(self, event, action, source):

		if ibid.sources[source].connect():
			event.addresponse(u'Connecting to %s' % source)
		else:
			event.addresponse(u"I couldn't connect to %s" % source)

class Disconnect(Module):

	@addressed
	@notprocessed
	@match('^\s*(disconnect)\s+(?:from\s+)?(\S+)\s*$')
	def process(self, event, action, source):

		if ibid.sources[source].disconnect():
			event.addresponse(u'Disconnecting from %s' % source)
		else:
			event.addresponse(u"I couldn't disconnect from %s" % source)
