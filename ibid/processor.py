from twisted.internet import reactor
import ibid.module
from traceback import print_exc

class Processor(object):

	def __init__(self, config):
		self.handlers = []
		self.sources = None
		self.config = config

		for module in config['modules']:
			self.load(module)

	def load(self, module):
		if isinstance(module, dict):
			name = module['name']
		else:
			name = module
			module = None
			for mod in self.config['modules']:
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
			self.handlers.append(moduleclass(module, self))
		except AttributeError:
			return False
		except TypeError:
			return False

		return True

	def unload(self, module):
		try:
			moduleclass = eval('ibid.module.%s.Module' % module)
		except AttributeError:
			return False

		for handler in self.handlers:
			if isinstance(handler, moduleclass):
				self.handlers.remove(handler)

		return True

	def _process(self, query, dispatch):
		for handler in self.handlers:
			try:
				result = handler.process(query)
				if result:
					query = result
			except Exception, e:
				print_exc()

		reactor.callFromThread(dispatch, query)

	def process(self, query, dispatch):
		reactor.callInThread(self._process, query, dispatch)

	def dispatch(self, query):
		for response in query['responses']:
			source = self.sources[response['source']]
			source.dispatch(response)
