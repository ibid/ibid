from ibid.module import Module
from ibid.decorators import *

class Greet(Module):

	@addressed
	@notprocessed
	@message
	@match('^\s*(?:hi|hello|hey)\s*$')
	def process(self, query):
		response = u'Hi %s' % query['user']
		query['responses'].append(response)
		query['processed'] = True
		return query
