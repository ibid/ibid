import re

import ibid.module


class Module(ibid.module.Module):

	def __init__(self):
		self.pattern = re.compile('\s*(hi|hello|hey)\s*', re.I)

	def process(self, query):
		if not query['addressed'] or query['processed']:
			return

		if not self.pattern.search(query['msg']):
			return

		response = 'Hi %s' % query['user']
		query['responses'].append(response)
		query['processed'] = True
		return query
