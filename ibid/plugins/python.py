import ibid
from ibid.plugins import Processor, match, authorise

class Eval(Processor):

	@match(r'^eval\s+(.+)$')
	@authorise('eval')
	def eval(self, event, code):
		try:
			globals = {}
			#exec('import os', globals)
			result = str(eval(code, globals, {}))
		except Exception, e:
			result = str(e)
		event.addresponse(result)
