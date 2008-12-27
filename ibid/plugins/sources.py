import ibid
from ibid.plugins import Processor, match, authorise

class Admin(Processor):

	@match('^\s*connect\s+(?:to\s+)?(\S+)\s*$')
	@authorise('sources')
	def connect(self, event, source):

		if ibid.sources[source].connect():
			event.addresponse(u'Connecting to %s' % source)
		else:
			event.addresponse(u"I couldn't connect to %s" % source)

	@match('^\s*disconnect\s+(?:from\s+)?(\S+)\s*$')
	@authorise('sources')
	def disconnect(self, event, source):

		if ibid.sources[source].disconnect():
			event.addresponse(u'Disconnecting from %s' % source)
		else:
			event.addresponse(u"I couldn't disconnect from %s" % source)

	@match('^\s*(?:re)?load\s+(\S+)\s+source\s*$')
	@authorise('sources')
	def load(self, event, source):
		if ibid.reloader.load_source(source, ibid.service):
			event.addresponse(u"%s source loaded" % source)
		else:
			event.addresponse(u"Couldn't load %s source" % source)

class Info(Processor):

	@match('^\s*list\s+sources\s*$')
	def list(self, event):
		event.addresponse(', '.join(ibid.sources.keys()))

	@match('^\s*list\s+configured\s+sources\s*$')
	def list(self, event):
		event.addresponse(', '.join(ibid.config.sources.keys()))
