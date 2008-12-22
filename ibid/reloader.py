from twisted.internet import reactor

import ibid
import ibid.dispatcher
import ibid.source.irc

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

	def load_sources(self):
		for source in ibid.core.config['sources']:
			self.load_source(source)

	def load_processors(self):
		for module in ibid.core.config['modules']:
			self.load_processor(module)

	def load_processor(self, module):
		if isinstance(module, dict):
			name = module['name']
		else:
			name = module
			module = None
			for mod in ibid.core.config['modules']:
				if mod['name'] == name:
					module = mod

			if not module:
				return False

		try:
			__import__('ibid.module.%s' % name)
		except ImportError:
			return False

		m = eval('ibid.module.%s' % name)
		reload(m)

		try:
			moduleclass = eval('ibid.module.%s.Module' % name)
			ibid.core.processors.append(moduleclass(module, self))
		except AttributeError:
			return False
		except TypeError:
			return False

		return True

	def unload_processor(self, module):
		try:
			moduleclass = eval('ibid.module.%s.Module' % module)
		except AttributeError:
			return False

		for handler in ibid.core.processors:
			if isinstance(handler, moduleclass):
				ibid.core.processors.remove(handler)

		return True
