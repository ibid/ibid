from time import sleep

from ibid.plugins import Processor, match
from ibid.config import IntOption

help = {}

help['coffee'] = u'Times coffee brewing and reserves cups for people'
class Coffee(Processor):
    """coffee (on|please)"""
    feature = 'coffee'

    pot = None

    time = IntOption('coffee_time', u'Brewing time in seconds', 240)
    cups = IntOption('coffee_cpus', u'Maximum number of cups', 4)
    
    @match(r'^coffee\s+on$')
    def coffee_on(self, event):
        # Hi ... race condition.
        if self.pot:
            event.addresponse(u"There's already a pot on")
            return event
        
        self.pot = [event.who]
        sleep(self.time)
        event.addresponse(u"Coffee's ready for %s!" % u', '.join(self.pot))
        self.pot = None
        return event
    
    @match('^coffee\s+(?:please|pls)$')
    def coffee_accept(self, event):
        if not self.pot:
            event.addresponse(u"There isn't a pot on.")

        elif len(self.pot) >= self.cups:
            event.addresponse(u"Sorry, there aren't any more cups left")

        else:
            self.pot.append(event.who)
            event.addresponse(True)

        return event

# vi: set et sta sw=4 ts=4:
