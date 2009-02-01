from httplib2 import Http
import re

from ibid.plugins import Processor, match, Option

help = {}

title = re.compile(r'<title>(.*)<\/title>', re.I+re.S)

help['get'] = 'Retrieves a URL and returns the HTTP status and optionally the HTML title.'
class HTTP(Processor):
	"""(get|head) <url>"""
	feature = 'get'

	max_size = Option('max_size', 'Only request this many bytes', 500, 'int')

	@match(r'^(get|head)\s+(.+)$')
	def handler(self, event, action, url):
		http = Http()
		headers={}
		if action.lower() == 'get':
			headers['Range'] = 'bytes=0-%s' % self.max_size
		response, content = http.request(url, action.upper(), headers=headers)
		reply = u'%s %s' % (response.status, response.reason)

		if action.lower() == 'get':
			match = title.search(content)
			if match:
				reply = u'%s "%s"' % (reply, match.groups()[0].strip())

		event.addresponse(reply)
		return event
