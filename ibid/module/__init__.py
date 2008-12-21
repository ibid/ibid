
class Module(object):

	def __init__(self, config):
		self.config = config
		print config

	def process(self, query):
		raise NotImplementedError
