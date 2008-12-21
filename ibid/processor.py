from twisted.internet import reactor

class Processor(object):

	def __init__(self):
		self.handlers = None
		self.sources = None

	def set_handlers(self, handlers):
		self.handlers = handlers

	def set_sources(self, sources):
		self.sources = sources

	def _process(self, query, dispatch):
		for handler in self.handlers:
			print "Trying %s" % handler
			result = handler.process(query)
			if result:
				query = result

		reactor.callFromThread(dispatch, query)

	def process(self, query, dispatch):
		reactor.callInThread(self._process, query, dispatch)

	def dispatch(self, query):
		for response in query['responses']:
			source = self.sources[response['source']]
			source.dispatch(response)
