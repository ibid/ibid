
class Event(dict):

	def __init__(self, source, type):
		self.source = source
		self.type = type
		self.responses = []
		self.processed = False

	def __getattr__(self, name):
		return self[name]

	def __setattr__(self, name, value):
		self[name] = value

	def addresponse(self, response, processed=True):
		self.responses.append(response)

		if processed:
			self.processed = True