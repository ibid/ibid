import ibid
from ibid.plugins import Processor, match

class Connect(Processor):

	@match('^\s*(connect)\s+(?:to\s+)?(\S+)\s*$')
	def handler(self, event, action, source):

		if ibid.sources[source].connect():
			event.addresponse(u'Connecting to %s' % source)
		else:
			event.addresponse(u"I couldn't connect to %s" % source)

class Disconnect(Processor):

	@match('^\s*(disconnect)\s+(?:from\s+)?(\S+)\s*$')
	def handler(self, event, action, source):

		if ibid.sources[source].disconnect():
			event.addresponse(u'Disconnecting from %s' % source)
		else:
			event.addresponse(u"I couldn't disconnect from %s" % source)
