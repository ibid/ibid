from urllib2 import urlopen
from threading import Timer

from trac.core import *
from trac.ticket import ITicketChangeListener

boturl = 'http://localhost:8080/'

def notify(ticket_id):
    urlopen('%s?m=ticket+%s' % (boturl, ticket_id)).close()

class IbidNotifier(Component):
    implements(ITicketChangeListener)

    def ticket_created(self, ticket):
        Timer(5, notify, [ticket.id]).start()

    def ticket_changed(self, ticket, comment, author, old_values):
        pass

    def ticket_deleted(self, ticket):
        pass

# vi: set et sta sw=4 ts=4:
