try:
	import perl
except ImportError:
	pass

import ibid
from ibid.plugins import Processor, match, authorise

class Python(Processor):

	@match(r'^py\s+(.+)$')
	@authorise('eval')
	def eval(self, event, code):
		try:
			globals = {}
			#exec('import os', globals)
			result = str(eval(code, globals, {}))
		except Exception, e:
			result = str(e)
		event.addresponse(result)

class Perl(Processor):

	@match(r'^perl\s+(.+)$')
	@authorise('eval')
	def eval(self, event, code):
		try:
			result = str(perl.eval(code))
		except Exception, e:
			result = str(e)

		event.addresponse(result)
