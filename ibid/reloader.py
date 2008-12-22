from twisted.internet import reactor

import ibid
import ibid.dispatcher
import ibid.source.irc

class Reloader(object):

	def run(self):
		self.reload_dispatcher()
		self.load_sources()
		self.load_processors()
		print ibid.core.processors
		reactor.run()

	def reload_dispatcher(self):
		reload(ibid.dispatcher)
		ibid.core.dispatcher = ibid.dispatcher.Dispatcher()
		
	def load_source(self, source):
		if source['type'] == 'irc':
			ibid.core.sources[source['name']] = ibid.source.irc.SourceFactory(source)
			reactor.connectTCP(source['server'], source['port'], ibid.core.sources[source['name']])

	def load_sources(self):
		for source in ibid.core.config['sources']:
			self.load_source(source)

	def load_processors(self):
		for module in ibid.core.config['modules']:
			self.load_processor(module)

	def load_processor(self, processor):
		if isinstance(processor, dict):
			name = processor['name']
		else:
			name = processor
			processor = None
			for mod in ibid.core.config['modules']:
				if mod['name'] == name:
					processor = mod

			if not module:
				return False

		module = 'ibid.module.' + name.split('.')[0]
		classname = 'ibid.module.' + name
		try:
			__import__(module)
		except ImportError:
			return False

		m = eval(module)
		reload(m)

		try:
			moduleclass = eval(classname)
			ibid.core.processors.append(moduleclass(processor, self))
		except AttributeError:
			return False
		except TypeError:
			return False

		return True

	def unload_processor(self, module):
		try:
			moduleclass = eval('ibid.module.%s' % module)
		except AttributeError:
			return False

		for processor in ibid.core.processors:
			if isinstance(processor, moduleclass):
				ibid.core.processors.remove(processor)

		return True
