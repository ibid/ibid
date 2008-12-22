from twisted.internet import reactor, ssl

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
		except ImportError:
			return False

		m = eval(module)
		reload(m)

		try:
			moduleclass = eval(classname)
			ibid.core.processors.append(moduleclass(name))
		except AttributeError:
			return False
		except TypeError:
			return False

		ibid.core.processors.sort(key=lambda x: ibid.core.config['processors'].index(x.name))

		return True

	def unload_processor(self, name):
		for processor in ibid.core.processors:
			if processor.name == name:
				ibid.core.processors.remove(processor)
				return True

		return False
