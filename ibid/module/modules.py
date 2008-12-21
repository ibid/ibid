import re
import os

import ibid.module

pattern = re.compile(r'^\s*(load|unload|reload)\s+(\S+)\s*$')

class Module(ibid.module.Module):

	def __init__(self, processor):
		self.processor = processor

	def _load(self, module):
		try:
			__import__('ibid.module.%s' % module)
		except ImportError:
			return u'Unable to import ibid.module.%s' % module

		m = eval('ibid.module.%s' % module)
		reload(m)

		try:
			moduleclass = eval('ibid.module.%s.Module' % module)
			self.processor.handlers.append(moduleclass())
		except AttributeError:
			return u'No Module class'
		except TypeError:
			return u'Module is not a class'

		return u'Loaded %s' % module

	def _unload(self, module):
		try:
			moduleclass = eval('ibid.module.%s.Module' % module)
		except AttributeError:
			return u"Module isn't loaded"

		for handler in self.processor.handlers:
			if isinstance(handler, moduleclass):
				self.processor.handlers.remove(handler)

		return u'Unloaded %s' % module

	def process(self, query):
		if not query['addressed'] or query['processed']:
			return

		match = pattern.search(query['msg'])
		if not match:
			return

		(action, module) = match.groups()

		if action == u'load':
			reply = self._load(module)
		elif action == u'unload':
			reply = self._unload(module)
		elif action == u'reload':
			self._unload(module)
			reply = self._load(module)

		query['responses'].append(reply)
		query['processed'] = True
		return query
