import random

import ibid
from ibid.plugins import Processor, match

help = {}

help['roshambo'] = 'Plays rock, paper, scissors.'
class RoShamBo(Processor):
	"""roshambo (rock|paper|scissors)"""
	feature = 'roshambo'

	@match(r'^roshambo\s+(rock|paper|scissors)$')
	def roshambo(self, event, choice):
		input = choice.lower()
		cpu = random.randint(0,2)
		list = ['paper', 'rock', 'scissors']
		
		if input == 'paper':
			input_number = 0
		elif input == 'rock':
			input_number = 1
		elif input == 'scissors':
			input_number = 2
	
		if input_number == cpu:
			reply = 'Draw %s %s' % (list[cpu], input)
		elif (input_number + 1) % 3 == cpu:
			reply = 'You win! I had: %s, You had: %s' % (list[cpu], input)
		else:
			reply = 'I win! I had: %s, You had: %s' % (list[cpu], input)
	
		event.addresponse(reply)
		return event
