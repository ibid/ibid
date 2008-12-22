from ibid.module import Module
from ibid.decorators import *

class Actions(Module):

	@addressed
	@notprocessed
	@message
	@match('^\s*(join|part|leave)\s+(#\S*)\s*$')
	def process(self, query, action, channel):
		if action == u'leave':
			action = 'part'

		ircaction = (action.lower(), channel)

		query['responses'].append({'reply': '%sing %s' % ircaction, 'ircaction': ircaction})
		query['processed'] = True
		return query
