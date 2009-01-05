from random import randint

import ibid
from ibid.plugins import Processor, match

help = {}

choices = ['paper', 'rock', 'scissors']

help['roshambo'] = 'Plays rock, paper, scissors.'
class RoShamBo(Processor):
    """roshambo (rock|paper|scissors)"""
    feature = 'roshambo'

    @match(r'^roshambo\s+(rock|paper|scissors)$')
    def roshambo(self, event, uchoice):
        uchoice = choices.index(uchoice.lower())
        bchoice = randint(0, 2)
 
        if uchoice == bchoice:
            reply = 'We drew! I also chose %s' % choices[bchoice]
        elif (uchoice + 1) % 3 == bchoice:
            reply = 'You win! I chose %s :-(' % choices[bchoice]
        else:
            reply = 'I win! I chose %s' % choices[bchoice]
 
        event.addresponse(reply)
        return event

# vi: set et sta sw=4 ts=4:
