from twisted.internet import reactor, ssl
from traceback import print_exc

import ibid
import ibid.dispatcher
import ibid.source.irc
import ibid.source.jabber

class Reloader(object):

	def run(self):
		self.reload_dispatcher()
		self.load_sources()
		self.load_processors()
		reactor.run()

	def reload_dispatcher(self):
		reload(ibid.dispatcher)
		ibid.core.dispatcher = ibid.dispatcher.Dispatcher()
		
	def load_source(self, source):
		if source['type'] == 'irc':
			ibid.core.sources[source['name']] = ibid.source.irc.SourceFactory(source)
			reactor.connectTCP(source['server'], source['port'], ibid.core.sources[source['name']])
		if source['type'] == 'jabber':
			ibid.core.sources[source['name']] = ibid.source.jabber.SourceFactory(source)
			reactor.connectSSL(source['server'], source['port'], ibid.core.sources[source['name']], ssl.ClientContextFactory())

	def load_sources(self):
		for source in ibid.core.config['sources']:
			self.load_source(source)

	def unload_source(self, name):
		if name not in ibid.core.sources:
			return False

		ibid.core.sources[name].protocol.loseConnection()
		del ibid.core.sources[name]

	def reload_source(self, name):
		if name not in ibid.core.config['sources']:
			return False

		self.unload_source(name)

		source = ibid.core.config['sources'][name]
		if source['type'] == 'irc':
			reload(ibid.source.irc)
		elif source['type'] == 'jabber':
			reload(ibid.source.jabber)

		self.load_source(source)

	def load_processors(self):
		for processor in ibid.core.config['processors']:
			self.load_processor(processor)

	def load_processor(self, name):
		type = name
		if name in ibid.core.config['modules'] and 'type' in ibid.core.config['modules'][name]:
			type = ibid.core.config['modules'][name]['type']

		module = 'ibid.module.' + type.split('.')[0]
		classname = 'ibid.module.' + type
		try:
			__import__(module)
		except Exception:
			print_exc()
			return False

		m = eval(module)
		reload(m)

		try:
			moduleclass = eval(classname)
			ibid.core.processors.append(moduleclass(name))
		except Exception:
			print_exc()
			return False

		ibid.core.processors.sort(key=lambda x: ibid.core.config['processors'].index(x.name))

		return True

	def unload_processor(self, name):
		for processor in ibid.core.processors:
			if processor.name == name:
				ibid.core.processors.remove(processor)
				return True

		return False
