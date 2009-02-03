from time import sleep

from pkg_resources import resource_exists, resource_string

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

version = resource_exists(__name__, '../.version') and resource_string(__name__, '../.version') or None

help['version'] = u"Show the Ibid version currently running"
class Version(Processor):
    """version"""
    feature = 'version'

    @match(r'^version$')
    def show_version(self, event):
        event.addresponse(version and u"I am version %s" % version or u"I don't know what version I am :-(")

# vi: set et sta sw=4 ts=4:
