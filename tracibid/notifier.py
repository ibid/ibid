# Copyright (c) 2009, Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from urllib import urlencode
from urllib2 import urlopen
from threading import Timer
try:
    from simplejson import dumps
except ImportError:
    from json import dumps

from trac.core import *
from trac.ticket import ITicketChangeListener
from trac.config import Option

def notify(url, data):
    urlopen(url, urlencode(data)).close()

class IbidNotifier(Component):
    implements(ITicketChangeListener)

    boturl = Option('tracibid', 'boturl', 'http://localhost:8080', 'URL of Ibid instance')

    def ticket_created(self, ticket):
        Timer(2, notify, [self.boturl+'/trac/ticket_created', {'id': ticket.id}]).start()

    def ticket_changed(self, ticket, comment, author, old_values):
        Timer(2, notify, [self.boturl+'/trac/ticket_changed', {'id': ticket.id, 'comment': comment, 'author': author, 'old_values': dumps(old_values)}]).start()

    def ticket_deleted(self, ticket):
        pass

# vi: set et sta sw=4 ts=4:
