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
