from datetime import datetime
from simplejson import loads
import logging

from sqlalchemy import Table, MetaData
from sqlalchemy.orm import mapper
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match, RPC
from ibid.config import Option, BoolOption
from ibid.utils import ago

help = {'trac': u'Retrieves tickets from a Trac database.'}

class Ticket(object):
    pass

session = ibid.databases.trac()
metadata = MetaData(bind=ibid.databases.trac().bind)
ticket_table = Table('ticket', metadata, autoload=True)
mapper(Ticket, ticket_table)
    
class Tickets(Processor, RPC):
    u"""ticket <number>
    (open|my|<who>'s) tickets"""
    feature = 'trac'

    url = Option('url', 'URL of Trac instance')
    source = Option('source', 'Source to send commit notifications to')
    channel = Option('channel', 'Channel to send commit notifications to')
    announce_changes = BoolOption('announce_changes', u'Announce changes to tickets', True)

    def __init__(self, name):
        Processor.__init__(self, name)
        RPC.__init__(self)
        self.log = logging.getLogger('plugins.trac')

    def get_ticket(self, id):
        session = ibid.databases.trac()
        ticket = session.query(Ticket).get(id)
        session.close()
        return ticket

    def remote_ticket_created(self, id):
        ticket = self.get_ticket(id)
        if not ticket:
            raise Exception(u"No such ticket")

        message = u'New %s in %s reported by %s: "%s" %sticket/%s' % (ticket.type, ticket.component, ticket.reporter, ticket.summary, self.url, ticket.id)
        ibid.dispatcher.send({'reply': message, 'source': self.source, 'target': self.channel})
        self.log.info(u'Ticket %s created', id)
        return True

    def remote_ticket_changed(self, id, comment, author, old_values):
        if not self.announce_changes:
            return False

        ticket = self.get_ticket(id)
        if not ticket:
            raise Exception(u'No such ticket')

        changes = []
        for field, old in old_values.items():
            if hasattr(ticket, field):
                changes.append(u'%s: %s' % (field, getattr(ticket, field)))
        if comment:
            changes.append(u'comment: "%s"' % comment)

        message = u'Ticket %s (%s %s %s in %s for %s) modified by %s. %s' % (id, ticket.status, ticket.priority, ticket.type, ticket.component, ticket.milestone, author, u', '.join(changes))
        ibid.dispatcher.send({'reply': message, 'source': self.source, 'target': self.channel})
        self.log.info(u'Ticket %s modified', id)
        return True

    @match(r'^ticket\s+(\d+)$')
    def get(self, event, number):
        ticket = self.get_ticket(int(number))

        if ticket:
            event.addresponse(u'Ticket %(id)s (%(status)s %(priority)s %(type)s in %(component)s for %(milestone)s) '
                u'reported %(ago)s ago assigned to %(owner)s: "%(summary)s" %(url)sticket/%(id)s', {
                'id': ticket.id,
                'status': ticket.status,
                'priority': ticket.priority,
                'type': ticket.type,
                'component': ticket.component,
                'milestone': ticket.milestone,
                'ago': ago(datetime.now() - datetime.fromtimestamp(ticket.time), 2),
                'owner': ticket.owner,
                'summary': ticket.summary, 
                'url': self.url,
            })
        else:
            event.addresponse(u"No such ticket")

    @match(r"^(?:(my|\S+?(?:'s))\s+)?(?:(open|closed|new|assigned)\s+)?tickets(?:\s+for\s+(.+?))?$")
    def handle_list(self, event, owner, status, milestone):
        session = ibid.databases.trac()

        status = status or 'open'
        if status.lower() == 'open':
            statuses = (u'new', u'assigned', u'reopened')
        else:
            statuses = (status.lower(),)
        
        query = session.query(Ticket).filter(Ticket.status.in_(statuses))

        if owner:
            if owner.lower() == 'my':
                owner = event.sender['nick']
            else:
                owner = owner.lower().replace("'s", '')
            query = query.filter(func.lower(Ticket.owner)==(owner.lower()))

        if milestone:
            query = query.filter_by(milestone=milestone)

        tickets = query.order_by(Ticket.id).all()

        if len(tickets) > 0:
            event.addresponse(u'%s', u', '.join(['%s (%s): "%s"' % (ticket.id, ticket.owner, ticket.summary) for ticket in tickets]))
        else:
            event.addresponse(u"No tickets found")

        session.close()

# vi: set et sta sw=4 ts=4:
