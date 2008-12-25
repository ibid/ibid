"""Displays help and usage of plugins and processors."""

import inspect

import ibid
from ibid.module import Module
from ibid.decorators import *


class Usage(Module):
	"""Usage: usage <processor>"""

	@addressed
	@notprocessed
	@match(r'^\s*usage\s+(.+)\s*$')
	def process(self, event, item):
		klass = None
		for processor in ibid.processors:
			if processor.name == item:
				klass = processor

		if not klass:
			try:
				klass = eval('ibid.module.%s' % item)
			except ImportError:
				pass

		if klass:
			event.addresponse(klass.__doc__)
		else:
			event.addresponse(u'No usage for %s' % item)

class Help(Module):
	"""Usage: help <plugin>"""

	@addressed
	@notprocessed
	@match(r'\s*help\s+(.+)\s*$')
	def process(self, event, item):
		try:
			module = eval('ibid.module.%s' % item)
		except:
			pass

		if module:
			if module.__doc__:
				event.addresponse(module.__doc__)
			processors = []
			for name, klass in inspect.getmembers(module, inspect.isclass):
				if issubclass(klass, ibid.module.Module) and klass != ibid.module.Module:
					processors.append(klass.__name__)
			event.addresponse('Processors: %s' % ', '.join(processors))
