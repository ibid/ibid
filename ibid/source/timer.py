from twisted.application import internet

import ibid
from ibid.source import IbidSourceFactory

class SourceFactory(IbidSourceFactory):

	def tick(self):
		event = Event(self.name, 'clock')
		ibid.core.dispatcher.dispatch(event)

	def setServiceParent(self, service):
		step = 1
		if 'step' in ibid.core.config['sources'][self.name]:
			step = ibid.core.config['sources'][self.name]['step']

		internet.TimerService(step, self.tick).setServiceParent(service)
