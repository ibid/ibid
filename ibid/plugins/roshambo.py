from random import randint

from ibid.plugins import Processor, match

help = {}

choices = ['paper', 'rock', 'scissors']

help['roshambo'] = u'Plays rock, paper, scissors.'
class RoShamBo(Processor):
    u"""roshambo (rock|paper|scissors)"""
    feature = 'roshambo'

    @match(r'^roshambo\s+(rock|paper|scissors)$')
    def roshambo(self, event, uchoice):
        uchoice = choices.index(uchoice.lower())
        bchoice = randint(0, 2)
 
        if uchoice == bchoice:
            reply = u'We drew! I also chose %s'
        elif (uchoice + 1) % 3 == bchoice:
            reply = u'You win! I chose %s :-('
        else:
            reply = u'I win! I chose %s'
 
        event.addresponse(reply, choices[bchoice])

# vi: set et sta sw=4 ts=4:
