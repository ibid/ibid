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

class Protected(Module):

    @addressed
    @notprocessed
    @match('^protected$')
    @authorised('protected')
    def process(self, event):
        event.addresponse('Executing protected command')

# vi: set et sta sw=4 ts=4:
