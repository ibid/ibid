import re

import ibid.module

class Module(ibid.module.Module):

	def __init__(self, config, processor):
		self.pattern = re.compile(r'^\s*(%s)([:;.?>!,-]+)*\s+' % '|'.join(config['names']), re.I)

	def process(self, query):
		if 'msg' not in query:
			return

		if 'addressed' not in query:
			newmsg = self.pattern.sub('', query['msg'])
			if newmsg != query['msg']:
				query["addressed"] = True
				query["msg"] = newmsg
			else:
				query["addressed"] = False
		return query
