from time import sleep

import ibid
from ibid.module import Module
from ibid.decorators import *

class Delay(Module):

    @addressed
    @notprocessed
    @match('^\s*delay\s+(\d+\.?\d*)\s*$')
    def process(self, event, delay):
        sleep(float(delay))
        event.addresponse('Done')
        return event

class TestPerm(Module):

    @addressed
    @notprocessed
    @match('^protected$')
    def process(self, event):

        if not ibid.auth.authenticate(event) or not ibid.auth.authorise(event, 'protected'):
            event.addresponse('Not authorised')
        else:
            event.addresponse('Authorised!')

# vi: set et sta sw=4 ts=4:
