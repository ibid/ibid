import ibid
from ibid.plugins import Processor, match, authorise

help = {'sources': 'Controls and lists the configured sources.'}

class Admin(Processor):
	"""(connect|disconnect) (to|from) <source>"""
	feature = 'sources'

	@match(r'^connect\s+(?:to\s+)?(\S+)$')
	@authorise('sources')
	def connect(self, event, source):

		if ibid.sources[source.lower()].connect():
			event.addresponse(u'Connecting to %s' % source)
		else:
			event.addresponse(u"I couldn't connect to %s" % source)

	@match(r'^disconnect\s+(?:from\s+)?(\S+)$')
	@authorise('sources')
	def disconnect(self, event, source):

		if ibid.sources[source.lower()].disconnect():
			event.addresponse(u'Disconnecting from %s' % source)
		else:
			event.addresponse(u"I couldn't disconnect from %s" % source)

	@match(r'^(?:re)?load\s+(\S+)\s+source$')
	@authorise('sources')
	def load(self, event, source):
		if ibid.reloader.load_source(source, ibid.service):
			event.addresponse(u"%s source loaded" % source)
		else:
			event.addresponse(u"Couldn't load %s source" % source)

class Info(Processor):
	"""sources"""
	feature = 'sources'

	@match(r'^sources$')
	def list(self, event):
		reply = u''
		for name, source in ibid.sources.items():
			reply += source.name
			if ibid.config.sources[source.name]['type'] == 'irc':
				reply += ' (irc://%s)' % ibid.config.sources[source.name]['server']
			elif ibid.config.sources[source.name]['type'] == 'jabber':
				reply += ' (xmpp://%s)' % ibid.config.sources[source.name]['jid'].split('/')[0]
			elif ibid.config.sources[source.name]['type'] == 'smtp':
				reply += ' (mailto:%s)' % ibid.config.sources[source.name]['address']
			elif ibid.config.sources[source.name]['type'] == 'http' and 'host' in ibid.config.sources[source.name]:
				reply += ' (http://%s%s)' % (ibid.config.sources[source.name]['host'], 'port' in ibid.config.sources[source.name] and ':%s' % ibid.config.sources[source.name]['port'] or '')
			reply += ', '
		reply = reply[:-2]
		event.addresponse(reply)

	@match(r'^list\s+configured\s+sources$')
	def listall(self, event):
		event.addresponse(', '.join(ibid.config.sources.keys()))
