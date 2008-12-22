import ibid

class Module(object):

	def __init__(self, config, processor):
		self.config = config
		self.processor = processor

	def process(self, query):
		raise NotImplementedError
