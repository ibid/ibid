from datetime import datetime

from sqlalchemy import Table, MetaData
from sqlalchemy.orm import mapper

import ibid
from ibid.plugins import Processor, match
from ibid.utils import ago

class Ticket(object):
	pass

session = ibid.databases.trac()
metadata = MetaData(bind=ibid.databases.trac().bind)
ticket_table = Table('ticket', metadata, autoload=True)
mapper(Ticket, ticket_table)
	
class GetTicket(Processor):

	@match(r'^ticket\s+(\d+)$')
	def get(self, event, number):
		session = ibid.databases.trac()
		ticket = session.query(Ticket).get(int(number))

		if ticket:
			event.addresponse(u"Ticket %s (%s %s %s) reported by %s %s ago and assigned to %s: %s" % (ticket.id, ticket.status, ticket.priority, ticket.type, ticket.reporter, ago(datetime.now() - datetime.fromtimestamp(ticket.time), 2), ticket.owner, ticket.summary))
		else:
			event.addresponse(u"No such ticket")

		session.close()
