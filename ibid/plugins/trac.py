from datetime import datetime

from sqlalchemy import Table, MetaData
from sqlalchemy.orm import mapper
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match
from ibid.utils import ago

help = {'trac': 'Retrieves tickets from a Trac database.'}

class Ticket(object):
    pass

session = ibid.databases.trac()
metadata = MetaData(bind=ibid.databases.trac().bind)
ticket_table = Table('ticket', metadata, autoload=True)
mapper(Ticket, ticket_table)
    
class GetTicket(Processor):
    """ticket <number>
    (open|my|<who>'s) tickets"""
    feature = 'trac'

    @match(r'^ticket\s+(\d+)$')
    def get(self, event, number):
        session = ibid.databases.trac()
        ticket = session.query(Ticket).get(int(number))

        if ticket:
            event.addresponse(u"Ticket %s (%s %s %s) reported by %s %s ago assigned to %s: %s" % (ticket.id, ticket.status, ticket.priority, ticket.type, ticket.reporter, ago(datetime.now() - datetime.fromtimestamp(ticket.time), 2), ticket.owner, ticket.summary))
        else:
            event.addresponse(u"No such ticket")

        session.close()

    @match(r"^(open|my|\S+?)(?:'s)?\s+tickets$")
    def list(self, event, what):
        if what.lower() == 'my':
            what = event.who

        session = ibid.databases.trac()
        tickets = session.query(Ticket)

        if what.lower() == 'open':
            tickets = tickets.filter(Ticket.status.in_(('new', 'assigned')))
        else:
            tickets = tickets.filter(func.lower(Ticket.owner)==what.lower())

        tickets = tickets.order_by(Ticket.id).all()

        event.addresponse(', '.join(['%s: "%s"' % (ticket.id, ticket.summary) for ticket in tickets]))
        session.close()

# vi: set et sta sw=4 ts=4:
