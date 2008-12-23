from time import sleep

import ibid
from ibid.module import Module, addresponse
from ibid.decorators import *

class Delay(Module):

	@addressed
	@notprocessed
	@match('^\s*delay\s+(\d+\.?\d*)\s*$')
	def process(self, event, delay):
		sleep(float(delay))
		addresponse(event, 'Done')
		return event
