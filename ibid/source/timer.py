from twisted.application import internet

import ibid
from ibid.event import Event
from ibid.source import IbidSourceFactory

class SourceFactory(IbidSourceFactory):

    def tick(self):
        event = Event(self.name, 'clock')
        ibid.dispatcher.dispatch(event)

    def setServiceParent(self, service):
        step = 1
        if 'step' in ibid.config.sources[self.name]:
            step = ibid.config.sources[self.name]['step']

        internet.TimerService(step, self.tick).setServiceParent(service)

# vi: set et sta sw=4 ts=4:
