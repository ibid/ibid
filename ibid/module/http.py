"""Performs HTTP requests"""

from httplib2 import Http
import re

import ibid
from ibid.module import Module
from ibid.decorators import *

title = re.compile(r'<title>(.*)<\/title>', re.I+re.S)

class HTTP(Module):
	"""Usage: (get|head) <url>"""

	@addressed
	@notprocessed
	@match('^\s*(get|head)\s+(.+)\s*$')
	def process(self, event, action, url):
		http = Http()
		headers={}
		if action.lower() == 'get':
			headers['Range'] = 'bytes=0-500'
		response, content = http.request(url, action.upper(), headers=headers)
		reply = u'%s %s' % (response.status, response.reason)

		if action.lower() == 'get':
			match = title.search(content)
			if match:
				reply = u'%s "%s"' % (reply, match.groups()[0].strip())

		event.addresponse(reply)
		return event
