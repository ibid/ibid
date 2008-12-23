from datetime import datetime
from time import strftime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

import ibid
from ibid.module import Module
from ibid.decorators import *

Base = declarative_base()
class Saw(Base):
	__tablename__ = 'seen'

	id = Column(Integer, primary_key=True)
	source = Column(String)
	user = Column(String)
	channel = Column(String)
	saying = Column(String)
	time = Column(DateTime)

	def __init__(self, source, user, channel, saying):
		self.source = source
		self.user = user
		self.channel = channel
		self.saying = saying
		self.time = datetime.now()

class Watch(Module):

	@message
	def process(self, event):
		saw = Saw(event.source, event.user, event.channel, event.message)
		session = ibid.databases['ibid']()
		session.add(saw)
		session.commit()

class Seen(Module):

	@addressed
	@notprocessed
	@match('^\s*seen\s+(\S+)\s*$')
	def process(self, event, who):
		session = ibid.databases['ibid']()
		saw = session.query(Saw).filter_by(user=who).first()
		if not saw:
			reply = "I haven't seen %s" % who
		else:
			reply = "Saw %s on %s in %s saying '%s'" % (saw.user, strftime('%Y/%m/%d %H:%M:%S', saw.time.timetuple()), saw.channel, saw.saying)

		event.addresponse(reply)
		return event
