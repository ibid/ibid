class Module(object):

	def __init__(self, name):
		self.name = name

	def process(self, query):
		raise NotImplementedError

def addresponse(event, response, processed=True):
	if 'responses' not in event:
		event['responses'] = []

	event['responses'].append(response)

	if processed:
		event['processed'] = True
