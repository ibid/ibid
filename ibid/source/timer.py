from twisted.application import internet

import ibid
from ibid.config import IntOption
from ibid.event import Event
from ibid.source import IbidSourceFactory

class SourceFactory(IbidSourceFactory):

    step = IntOption('step', 'Timer interval in seconds', 1)

    def tick(self):
        event = Event(self.name, u'clock')
        ibid.dispatcher.dispatch(event)

    def setServiceParent(self, service):
        self.s = internet.TimerService(self.step, self.tick)
        if service is None:
            self.s.startService()
        else:
            self.s.setServiceParent(service)

    def disconnect(self):
        self.s.stopService()
        return True

# vi: set et sta sw=4 ts=4:
