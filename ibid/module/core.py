import re

import ibid
from ibid.module import Module
from ibid.decorators import *

class Addressed(Module):

	def __init__(self, name):
		Module.__init__(self, name)
		self.pattern = re.compile(r'^\s*(%s)([:;.?>!,-]+)*\s+' % '|'.join(ibid.core.config['modules'][name]['names']), re.I)

	@message
	def process(self, event):
		if 'addressed' not in event:
			newmsg = self.pattern.sub('', event.message)
			if newmsg != event.message:
				event.addressed = True
				event.message = newmsg
			else:
				event.addressed = False
		return event

class Ignore(Module):

	@addressed
	@notprocessed
	@message
	def process(self, event):
		for who in ibid.core.config['modules'][self.name]['ignore']:
			if event.user == who:
				event.processed = True

		return event

class Responses(Module):

	def process(self, event):
		if 'responses' not in event:
			return

		converted = []
		for response in event.responses:
			if isinstance(response, basestring):
				response = {'reply': response}
			if 'target' not in response:
				response['target'] = event.channel
			if 'source' not in response:
				response['source'] = event.source
			converted.append(response)

		event.responses = converted
		return event
