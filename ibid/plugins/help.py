import inspect

import ibid
from ibid.plugins import Processor, match

help = {'help': 'Provides help and usage information about plugins.'}

class Help(Processor):
	"""(help|usage) [<feature>]"""
	feature = 'help'

	@match(r'^help$')
	def features(self, event):
		features = []

		for processor in ibid.processors:
			module = eval(processor.__module__)
			if hasattr(module, 'help'):
				for feature in module.help.keys():
					if feature not in features:
						features.append(feature)

		event.addresponse(u' '.join(features))

	@match(r'^help\s+(.+)$')
	def help(self, event, feature):
		feature = feature.lower()

		for processor in ibid.processors:
			module = eval(processor.__module__)
			if hasattr(module, 'help') and feature in module.help:
				event.addresponse(module.help[feature])
				return

		event.addresponse(u"I can't help you with %s" % feature)

	@match(r'^(?:usage|how\s+do\s+I\s+use)\s+(.+)$')
	def usage(self, event, feature):
		feature = feature.lower()

		for processor in ibid.processors:
			for name, klass in inspect.getmembers(processor, inspect.isclass):
				if hasattr(klass, 'feature') and klass.feature == feature and klass.__doc__:
					for line in klass.__doc__.splitlines():
						event.addresponse('Usage: %s' % line.strip())

		if not event.responses:
			event.addresponse(u"I don't know how to use %s either" % feature)
