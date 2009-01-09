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

help = {'eval': 'Evaluates Python, Perl and Lua code.'}

class Python(Processor):
	"""py <code>"""
	feature = 'eval'

	@match(r'^py(?:thon)?\s+(.+)$')
	@authorise('eval')
	def eval(self, event, code):
		try:
			globals = {}
			exec('import os', globals)
			exec('import sys', globals)
			exec('import re', globals)
			result = str(eval(code, globals, {}))
		except Exception, e:
			result = str(e)
		event.addresponse(result)

class Perl(Processor):
	"""pl <code>"""
	feature = 'eval'

	@match(r'^(?:perl|pl)\s+(.+)$')
	@authorise('eval')
	def eval(self, event, code):
		try:
			result = perl.eval(code)
		except Exception, e:
			result = e

		event.addresponse(str(result))

class Lua(Processor):
	"""lua <code>"""
	feature = 'eval'

	@match(r'^lua\s+(.+)$')
	@authorise('eval')
	def eval(self, event, code):
		try:
			result = lua.eval(code)
		except Exception, e:
			result = e

		event.addresponse(str(result))
