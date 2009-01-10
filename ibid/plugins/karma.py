from datetime import datetime
import re

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match, handler

Base = declarative_base()

class Karma(Base):
    __tablename__ = 'karma'

    id = Column(Integer, primary_key=True)
    subject = Column(Unicode)
    karma = Column(Integer)
    time = Column(DateTime)

    def __init__(self, subject):
        self.subject = subject
        self.karma = 0
        self.time = datetime.now()

class Set(Processor):

    increase = ('++', 'ftw')
    decrease = ('--', 'ftl')
    neutral = ('==',)
    reply = True

    def setup(self):
        self.set.im_func.pattern = re.compile(r'^(.+?)\s*(%s)\s*(?:[[{(]+(.+?)[\]})]+)?' % '|'.join([re.escape(token) for token in self.increase + self.decrease + self.neutral]), re.I)

    @handler
    def set(self, event, subject, adjust, reason):
        print reason
        session = ibid.databases.ibid()
        karma = session.query(Karma).filter(func.lower(Karma.subject)==subject.lower()).first()
        if not karma:
            karma = Karma(subject)

        if adjust.lower() in self.increase:
            karma.karma += 1
        elif adjust.lower() in self.decrease:
            karma.karma -= 1

        session.add(karma)
        session.commit()
        session.close()

        if self.reply:
            event.addresponse(True)

class Get(Processor):

    @match(r'^karma\s+(?:for\s+)?(.+)$')
    def handle_karma(self, event, subject):
        session = ibid.databases.ibid()
        karma = session.query(Karma).filter(func.lower(Karma.subject)==subject.lower()).first()
        if not karma:
            event.addresponse(u"%s has neutral karma" % subject)
        else:
            event.addresponse(u"%s has karma of %s" % (subject, karma.karma))

    @match(r'^(reverse\s+)?karmaladder$')
    def ladder(self, event, reverse):
        session = ibid.databases.ibid()
        karmas = session.query(Karma).order_by(reverse and Karma.karma.asc() or Karma.karma.desc()).limit(30).all()
        event.addresponse(', '.join(['%s: %s (%s)' % (karmas.index(karma), karma.subject, karma.karma) for karma in karmas]))

# vi: set et sta sw=4 ts=4: