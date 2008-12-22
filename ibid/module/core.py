import re

import ibid
from ibid.module import Module
from ibid.decorators import *

class Addressed(Module):

	def __init__(self, name):
		Module.__init__(self, name)
		self.pattern = re.compile(r'^\s*(%s)([:;.?>!,-]+)*\s+' % '|'.join(ibid.core.config['modules'][name]['names']), re.I)

	@message
	def process(self, query):
		if 'addressed' not in query:
			newmsg = self.pattern.sub('', query['msg'])
			if newmsg != query['msg']:
				query["addressed"] = True
				query["msg"] = newmsg
			else:
				query["addressed"] = False
		return query

class Ignore(Module):

	@addressed
	@notprocessed
	@message
	def process(self, query):
		for who in ibid.core.config['modules'][self.name]['ignore']:
			if query['user'] == who:
				query['processed'] = True

		return query

class Responses(Module):

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
