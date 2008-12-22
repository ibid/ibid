import re
import os

import ibid
from ibid.module import Module
from ibid.decorators import *


pattern1 = re.compile(r'^\s*(load|unload|reload)\s+(\S+)\s*$')
pattern2 = re.compile(r'^\s*lsmod\s*$')

class Modules(Module):

	def list(self):
		reply = ''
		for handler in self.processor.handlers:
			name = handler.__module__.split('.', 2)[2]
			reply = u'%s%s, ' % (reply, name)
		return reply

	@addressed
	@notprocessed
	@message
	def process(self, query):
		reply = None

		match = pattern1.search(query['msg'])
		if match:
			(action, module) = match.groups()

			if action == u'load':
				reply = ibid.core.reloader.load_processor(module)
				reply = reply and u'Loaded %s' % module or u"Couldn't load %s" % module
			elif action == u'unload':
				reply = ibid.core.reloader.unload_processor(module)
				reply = reply and u'Unloaded %s' % module or u"Couldn't unload %s" % module
			elif action == u'reload':
				if module == u'reloader':
					ibid.core.reload_reloader()
					reply = "Done"
				elif module == u'dispatcher':
					ibid.core.reloader.reload_dispatcher()
					reply = "done"
				else:
					ibid.core.reloader.unload_processor(module)
					reply = ibid.core.reloader.load_processor(module)
					reply = reply and u'Reloaded %s' % module or u"Couldn't reload %s" % module

		match = pattern2.search(query['msg'])
		if match:
			reply = self.list()

		if reply:
			query['responses'].append(reply)
			query['processed'] = True
			return query
