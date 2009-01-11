from sqlalchemy import Table, MetaData
from sqlalchemy.orm import mapper
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match

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

		event.addresponse(u"Ticket %s (%s) reported by %s: %s" % (ticket.id, ticket.status, ticket.reporter, ticket.summary))
