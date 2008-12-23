import ibid

class IbidSourceFactory(object):

	def __init__(self, name):
		self.name = name

	def setServiceParent(self, service):
		raise NotImplementedError

	def connect(self):
		raise NotImplementedError
