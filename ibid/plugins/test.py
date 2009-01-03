from time import sleep

import ibid
from ibid.plugins import Processor, match, authorise

class Delay(Processor):

    @match(r'^delay\s+(\d+\.?\d*)$')
    def handler(self, event, delay):
        sleep(float(delay))
        event.addresponse('Done')
        return event

class Protected(Processor):

    @match(r'^protected$')
    @authorise('protected')
    def handler(self, event):
        event.addresponse('Executing protected command')

class Email(Processor):

    @match(r'^email\s+(.+)$')
    def email(self, event, address):
        event.addresponse({'reply': 'Test message', 'source': 'email', 'target': unicode(address)})
        event.addresponse(u"I've emailed %s" % address)

# vi: set et sta sw=4 ts=4:
