import ibid.module

class Module(ibid.module.Module):

	def process(self, query):
		converted = []
		for response in query['responses']:
			if isinstance(response, basestring):
				response = {'reply': response}
			if 'target' not in response:
				response['target'] = query['channel']
			if 'source' not in response:
				response['source'] = query['source']
			converted.append(response)

		query['responses'] = converted
		return query
