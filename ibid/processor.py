
class Processor(object):

	def __init__(self):
		self.handlers = None
		self.sources = None

	def set_handlers(self, handlers):
		self.handlers = handlers

	def set_sources(self, sources):
		self.sources = sources

	def process(self, query, dispatch):
		for handler in self.handlers:
			query = handler.process(query)

		dispatch(query)

	def dispatch(self, query):
		for response in query['responses']:
			source = self.sources[response['source']]
			source.dispatch(response)
