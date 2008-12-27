"""Displays help and usage of plugins and processors."""

import inspect

import ibid
from ibid.plugins import Processor, match

class Usage(Processor):
	"""Outputs the usage syntax for a processor"""

	@match(r'^\s*usage\s+(.+)\s*$')
	def handler(self, event, item):
		"""Usage: usage <processor>"""
		klass = None
		for processor in ibid.processors:
			if processor.name == item:
				klass = processor

		if not klass:
			try:
				klass = eval('ibid.plugins.%s' % item)
			except:
				pass

		if klass:
			for name, method in inspect.getmembers(klass, inspect.ismethod):
				if hasattr(method, 'pattern') and method.__doc__:
					event.addresponse('%s: %s' % (name, method.__doc__))

		if not event.responses:
			event.addresponse(u'No usage for %s' % item)

class Help(Processor):
	"""Outputs the help message for a plugin or processor"""

	@match(r'\s*help\s+(.+)\s*$')
	def handler(self, event, item):
		"""Usage: help <plugin>"""
		try:
			module = eval('ibid.plugins.%s' % item)
		except:
			pass

		if module:
			if module.__doc__:
				event.addresponse(module.__doc__)
			processors = []
			for name, klass in inspect.getmembers(module, inspect.isclass):
				if issubclass(klass, ibid.plugins.Module) and klass != ibid.plugins.Processor:
					processors.append('%s.%s' % (module.__name__.replace('ibid.plugins.', '', 1), klass.__name__))
			if processors:
				event.addresponse('Processors: %s' % ', '.join(processors))
