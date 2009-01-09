try:
	import perl
except ImportError:
	pass

try:
	import lua
except ImportError:
	pass

import ibid
from ibid.plugins import Processor, match, authorise

class Python(Processor):

	@match(r'^py(?:thon)?\s+(.+)$')
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

	@match(r'^(?:perl|pl)\s+(.+)$')
	@authorise('eval')
	def eval(self, event, code):
		try:
			result = perl.eval(code)
		except Exception, e:
			result = e

		event.addresponse(str(result))

class Lua(Processor):

	@match(r'^lua\s+(.+)$')
	@authorise('eval')
	def eval(self, event, code):
		try:
			result = lua.eval(code)
		except Exception, e:
			result = e

		event.addresponse(str(result))
