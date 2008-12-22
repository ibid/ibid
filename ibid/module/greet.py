import re

import ibid.module

pattern = re.compile(r'^\s*(hi|hello|hey)\s*$', re.I)

class Module(ibid.module.Module):

	def process(self, query):
		if not query['addressed'] or query['processed'] or 'msg' not in query:
			return

		if not pattern.search(query['msg']):
			return

		response = u'Hi %s' % query['user']
		query['responses'].append(response)
		query['processed'] = True
		return query
