"""Displays help and usage of plugins and processors."""

import inspect

import ibid
from ibid.module import Module
from ibid.decorators import *


class Usage(Module):
	"""Outputs the usage syntax for a processor"""

	@addressed
	@notprocessed
	@match(r'^\s*usage\s+(.+)\s*$')
	def process(self, event, item):
		"""Usage: usage <processor>"""
		klass = None
		for processor in ibid.processors:
			if processor.name == item:
				klass = processor

		if not klass:
			try:
				klass = eval('ibid.module.%s' % item)
			except:
				pass

		if klass:
			for name, method in inspect.getmembers(klass, inspect.ismethod):
				if hasattr(method, 'pattern') and method.__doc__:
					event.addresponse('%s: %s' % (name, method.__doc__))

		if not event.responses:
			event.addresponse(u'No usage for %s' % item)

class Help(Module):
	"""Outputs the help message for a plugin or processor"""

	@addressed
	@notprocessed
	@match(r'\s*help\s+(.+)\s*$')
	def process(self, event, item):
		"""Usage: help <plugin>"""
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
					processors.append('%s.%s' % (module.__name__.replace('ibid.module.', '', 1), klass.__name__))
			if processors:
				event.addresponse('Processors: %s' % ', '.join(processors))
