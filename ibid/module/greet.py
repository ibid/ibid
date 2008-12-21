
class Module(object):

	def process(self, query):
		response = {'target': query['channel'], 'reply': 'Hi!'}
		query['responses'] = [response]
		return query
