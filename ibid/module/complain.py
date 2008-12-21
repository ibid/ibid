import random

import ibid.module

complaints = ('Huh?', 'Sorry', '?', 'Excuse me?')

class Module(ibid.module.Module):

	def process(self, query):
		if not query['addressed'] or query['processed']:
			return

		reply = complaints[random.randrange(len(complaints))]
		if query['public']:
			reply = '%s: %s' % (query['user'], reply)

		query['responses'].append(reply)
		query['processed'] = True
		return query
