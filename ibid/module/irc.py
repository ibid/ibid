import re

import ibid.module

pattern = re.compile(r'^\s*(join|part|leave)\s+(#\S*)\s*$')

class Module(ibid.module.Module):

	def process(self, query):
		if not query['addressed'] or query['processed'] or 'msg' not in query:
			return

		match = pattern.search(query['msg'])
		if not match:
			return

		(action, channel) = match.groups()
		if action == u'leave':
			action = 'part'

		ircaction = (action.lower(), channel)

		query['responses'].append({'reply': '%sing %s' % ircaction, 'ircaction': ircaction})
		query['processed'] = True
		return query
