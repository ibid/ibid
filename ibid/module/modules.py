import re
import os

import ibid.module

pattern1 = re.compile(r'^\s*(load|unload|reload)\s+(\S+)\s*$')
pattern2 = re.compile(r'^\s*lsmod\s*$')

class Module(ibid.module.Module):

	def __init__(self, processor):
		self.processor = processor

	def load(self, module, config):
		try:
			__import__('ibid.module.%s' % module)
		except ImportError:
			return u'Unable to import ibid.module.%s' % module

		m = eval('ibid.module.%s' % module)
		reload(m)

		try:
			moduleclass = eval('ibid.module.%s.Module' % module)
			self.processor.handlers.append(moduleclass(config))
		except AttributeError:
			return u'No Module class'
		except TypeError:
			return u'Module is not a class'

		return u'Loaded %s' % module

	def unload(self, module):
		try:
			moduleclass = eval('ibid.module.%s.Module' % module)
		except AttributeError:
			return u"Module isn't loaded"

		for handler in self.processor.handlers:
			if isinstance(handler, moduleclass):
				self.processor.handlers.remove(handler)

		return u'Unloaded %s' % module

	def list(self):
		reply = ''
		for handler in self.processor.handlers:
			name = handler.__module__.split('.', 2)[2]
			reply = u'%s%s, ' % (reply, name)
		return reply

	def process(self, query):
		if not query['addressed'] or query['processed']:
			return

		reply = None

		match = pattern1.search(query['msg'])
		if match:
			(action, module) = match.groups()

			if action == u'load':
				reply = self.load(module)
			elif action == u'unload':
				reply = self.unload(module)
			elif action == u'reload':
				self.unload(module)
				reply = self.load(module)
			elif action == u'lsmod':
				reply = self.list()

		match = pattern2.search(query['msg'])
		if match:
			reply = self.list()

		if reply:
			query['responses'].append(reply)
			query['processed'] = True
			return query
