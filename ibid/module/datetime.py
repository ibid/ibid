import time
import re

import ibid.module

pattern = re.compile('\s*(date|time)\s*', re.I)

class Module(ibid.module.Module):

	def process(self, query):
		if not query['addressed'] or query['processed']:
			return

		if not pattern.search(query['msg']):
			return

		reply = time.strftime("It is %H:%M.%S on %a, %e %b %Y",time.localtime())
		if query['public']:
			reply = '%s: %s' % (query['user'], reply)

		query['responses'].append(reply)
		query['processed'] = True
		return query
