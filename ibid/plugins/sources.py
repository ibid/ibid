import ibid
from ibid.plugins import Processor, match, authorise

class Admin(Processor):

	@match(r'^\s*connect\s+(?:to\s+)?(\S+)\s*$')
	@authorise('sources')
	def connect(self, event, source):

		if ibid.sources[source.lower()].connect():
			event.addresponse(u'Connecting to %s' % source)
		else:
			event.addresponse(u"I couldn't connect to %s" % source)

	@match(r'^\s*disconnect\s+(?:from\s+)?(\S+)\s*$')
	@authorise('sources')
	def disconnect(self, event, source):

		if ibid.sources[source.lower()].disconnect():
			event.addresponse(u'Disconnecting from %s' % source)
		else:
			event.addresponse(u"I couldn't disconnect from %s" % source)

	@match(r'^\s*(?:re)?load\s+(\S+)\s+source\s*$')
	@authorise('sources')
	def load(self, event, source):
		if ibid.reloader.load_source(source, ibid.service):
			event.addresponse(u"%s source loaded" % source)
		else:
			event.addresponse(u"Couldn't load %s source" % source)

class Info(Processor):

	@match(r'^sources$')
	def list(self, event):
		reply = u''
		for name, source in ibid.sources.items():
			reply += source.name
			if ibid.config.sources[source.name]['type'] == 'irc':
				reply += ' (%s)' % ibid.config.sources[source.name]['server']
			elif ibid.config.sources[source.name]['type'] == 'jabber':
				reply += ' (%s)' % ibid.config.sources[source.name]['jid'].split('/')[0]
			reply += ', '
		reply = reply[:-2]
		event.addresponse(reply)

	@match(r'^list\s+configured\s+sources$')
	def listall(self, event):
		event.addresponse(', '.join(ibid.config.sources.keys()))
