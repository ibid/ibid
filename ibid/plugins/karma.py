from datetime import datetime
import re
import logging

from sqlalchemy import Column, Integer, Unicode, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match, handler, authorise, Option, boolean

help = {'karma': u'Keeps track of karma for people and things.'}

Base = declarative_base()

log = logging.getLogger('plugins.karma')

class Karma(Base):
    __tablename__ = 'karma'

    id = Column(Integer, primary_key=True)
    subject = Column(Unicode(128), unique=True, nullable=False)
    changes = Column(Integer, nullable=False)
    value = Column(Integer, nullable=False)
    time = Column(DateTime, nullable=False, default=func.current_timestamp())

    def __init__(self, subject):
        self.subject = subject
        self.changes = 0
        self.value = 0

class Set(Processor):
    """<subject> (++|--|==|ftw|ftl) [[reason]]"""
    feature = 'karma'

    permission = u'karma'

    increase = Option('increase', 'Suffixes which indicate increased karma', ('++', 'ftw'))
    decrease = Option('decrease', 'Suffixes which indicate decreased karma', ('--', 'ftl'))
    neutral = Option('neutral', 'Suffixes which indicate neutral karma', ('==',))
    reply = Option('reply', 'Acknowledge karma changes', False, 'bool')
    public = Option('public', 'Only allow karma changes in public', True, 'bool')
    ignore = Option('ignore', 'Karma subjects to silently ignore', ())

    def setup(self):
        self.set.im_func.pattern = re.compile(r'^(.+?)\s*(%s)\s*(?:[[{(]+\s*(.+?)\s*[\]})]+)?' % '|'.join([re.escape(token) for token in self.increase + self.decrease + self.neutral]), re.I)

    @handler
    @authorise
    def set(self, event, subject, adjust, reason):
        if self.public and not event.public:
            event.addresponse(u"Karma must be done in public")
            return

        if subject.lower() in self.ignore:
            return

        session = ibid.databases.ibid()
        karma = session.query(Karma).filter(func.lower(Karma.subject)==subject.lower()).first()
        if not karma:
            karma = Karma(subject)

        if adjust.lower() in self.increase:
            if subject.lower() == event.who.lower():
                event.addresponse(u"You can't karma yourself!")
                return
            karma.changes += 1
            karma.value += 1
            change = u'Increased'
        elif adjust.lower() in self.decrease:
            karma.changes += 1
            karma.value -= 1
            change = u'Decreased'
        else:
            karma.changes += 2
            change = u'Increased and decreased'

        session.save_or_update(karma)
        session.flush()
        session.close()

        log.info(u"%s karma for '%s' by %s/%s (%s) because: %s", change, subject, event.account, event.identity, event.sender, reason)

        if self.reply:
            event.addresponse(True)

class Get(Processor):
    """karma for <subject>
    [reverse] karmaladder"""
    feature = 'karma'

    @match(r'^karma\s+(?:for\s+)?(.+)$')
    def handle_karma(self, event, subject):
        session = ibid.databases.ibid()
        karma = session.query(Karma).filter(func.lower(Karma.subject)==subject.lower()).first()
        if not karma:
            event.addresponse(u"%s has neutral karma" % subject)
        else:
            event.addresponse(u"%s has karma of %s" % (subject, karma.value))
        session.close()

    @match(r'^(reverse\s+)?karmaladder$')
    def ladder(self, event, reverse):
        session = ibid.databases.ibid()
        karmas = session.query(Karma).order_by(reverse and Karma.value.asc() or Karma.value.desc()).limit(30).all()
        event.addresponse(', '.join(['%s: %s (%s)' % (karmas.index(karma), karma.subject, karma.value) for karma in karmas]))
        session.close()

# vi: set et sta sw=4 ts=4:
