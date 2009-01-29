from urllib2 import urlopen
from threading import Timer

from trac.core import *
from trac.ticket import ITicketChangeListener
from trac.config import Option

def notify(boturl, ticket_id):
    urlopen('%s/trac/newticket/%s' % (boturl, ticket_id)).close()

class IbidNotifier(Component):
    implements(ITicketChangeListener)

    boturl = Option('tracibid', 'boturl', 'http://localhost:8080', 'URL of Ibid instance')

    def ticket_created(self, ticket):
        Timer(5, notify, [self.boturl, ticket.id]).start()

    def ticket_changed(self, ticket, comment, author, old_values):
        pass

    def ticket_deleted(self, ticket):
        pass

# vi: set et sta sw=4 ts=4:
