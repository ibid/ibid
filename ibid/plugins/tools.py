import re

import ibid
from ibid.plugins import Processor, match

help = {}

help['retest'] = 'Checks whether a regular expression matches a given string.'
class ReTest(Processor):
	"""does <pattern> match <string>"""
	feature = 'retest'

	@match('^does\s+(.+?)\s+match\s+(.+?)$')
	def retest(self, event, regex, string):
		event.addresponse(re.search(regex, string) and 'Yes' or 'No')
