from datetime import datetime

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

import ibid
from ibid.plugins import Processor, match

Base = declarative_base()

class URL(Base):
	__tablename__ = 'urls'

	id = Column(Integer, primary_key=True)
	url = Column(Unicode)
	channel = Column(Unicode)
	identity = Column(Integer)
	time = Column(DateTime)

	def __init__(self, url, channel, identity):
		self.url = url
		self.channel = channel
		self.identity = identity
		self.time = datetime.now()

class Grab(Processor):

	addressed = False
	processed = True

	@match(r'((?:\S+://|(?:www|ftp)\.)\S+|\S+\.(?:com|org|net|za))')
	def grab(self, event, url):
		if url.find('://') == -1:
			if url.lower().startswith('ftp'):
				url = 'ftp://%s' % url
			else:
				url = 'http://%s' % url

		session = ibid.databases.ibid()
		u = URL(url, event.channel, event.identity)
		session.add(u)
		session.commit()
		session.close()
