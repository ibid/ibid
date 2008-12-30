"""Displays help and usage of plugins and processors."""

import inspect

import ibid
from ibid.plugins import Processor, match, provides

help = {'help': 'Provides help and usage information about plugins.'}

class Features(Processor):
	"""help"""
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

		event.addresponse(' '.join(features))

class Help(Processor):
	"""help [<feature>]"""
	feature = 'help'

	@match(r'^help\s+(.+)$')
	def handler(self, event, feature):
		feature = feature.lower()

		for processor in ibid.processors:
			module = eval(processor.__module__)
			if hasattr(module, 'help') and feature in module.help:
				event.addresponse(module.help[feature])
				return

		event.addresponse(u"I can't help you with %s" % feature)

class Usage(Processor):
	"""usage <feature>"""
	feature = 'help'

	@match(r'\s*usage\s+(.+)\s*$')
	def handler(self, event, feature):
		feature = feature.lower()

		for processor in ibid.processors:
			for name, klass in inspect.getmembers(processor, inspect.isclass):
				if hasattr(klass, 'feature') and klass.feature == feature and klass.__doc__:
					event.addresponse('Usage: %s' % klass.__doc__)

		if not event.responses:
			event.addresponse(u"Um, I don't know how to use %s either" % feature)
