import re
from random import random, randint

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

help['random'] = 'Generates random numbers.'
class Random(Processor):
	"""random [ <max> | <min> <max> ]"""
	feature = 'random'

	@match('^random(?:\s+(\d+)(?:\s+(\d+))?)?$')
	def random(self, event, begin, end):
		if not begin and not end:
			event.addresponse(str(random()))
		else:
			begin = int(begin)
			end = end and int(end) or 0
			event.addresponse(str(randint(min(begin,end), max(begin,end))))
