import sys

import ibid
from ibid.module import Module
from ibid.decorators import *


class Proxy(Module):

	def __init__(self, name):
		Module.__init__(self, name)
		bus_name = ibid.core.config['modules'][name]['bus_name']
		object_path = ibid.core.config['modules'][name]['object_path']
		bus = sys.modules['dbus'].SessionBus()
		object = bus.get_object(bus_name, object_path)
		self.iface = sys.modules['dbus'].Interface(object, 'org.ibid.ModuleInterface')
		regex = self.iface.init(name)
		self.pattern = re.compile(regex, re.I)

	@addressed
	@notprocessed
	def process(self, event):
		if not self.pattern.search(event['msg']):
			return

		converted = event.copy()
		if 'responses' in converted:
			del converted['responses']
		for key, value in converted.items():
			converted[key] = str(value)
		print converted

		response = self.iface.process(converted)
		dir(response)

		if response:
			event['responses'].append(response)
			event['processed'] = True
			return event
