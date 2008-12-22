import time

from ibid.module import Module
from ibid.decorators import *

class DateTime(Module):

	@addressed
	@notprocessed
	@message
	@match('^\s*(?:date|time)\s*$')
	def process(self, query):
		reply = time.strftime(u"It is %H:%M.%S on %a, %e %b %Y",time.localtime())
		if query['public']:
			reply = u'%s: %s' % (query['user'], reply)

		query['responses'].append(reply)
		query['processed'] = True
		return query
