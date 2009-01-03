from datetime import datetime

from sqlalchemy import Column, Integer, Unicode, DateTime, or_, ForeignKey
from sqlalchemy.orm import relation, backref
from sqlalchemy.ext.declarative import declarative_base

import ibid
from ibid.plugins import Processor, match

Base = declarative_base()

class Fact(Base):
    __tablename__ = 'facts'

    id = Column(Integer, primary_key=True)
    fact = Column(Unicode)
    verb = Column(Unicode)
    factoid = Column(Integer)
    factoids = relation('Factoid')
    who = Column(Unicode)
    time = Column(DateTime)

    def __init__(self, fact, verb, factoid, who=None):
        self.fact = fact
        self.verb = verb
        self.factoid = factoid
        self.who = who
        self.time = datetime.now()

    def __repr__(self):
        return u'<Fact %s %s %s>' % (self.fact, self.verb, self.factoid)

class Factoid(Base):
    __tablename__ = 'factoids'

    id = Column(Integer, primary_key=True)
    value = Column(Unicode)
    factoid = Column(Integer, ForeignKey('facts.factoid'))
    fact = relation(Fact)
    who = Column(Unicode)
    time = Column(DateTime)

    def __init__(self, value, factoid, who=None):
        self.value = value
        self.factoid = factoid
        self.who = who
        self.time = datetime.now()

    def __repr__(self):
        return u'<Factoid %s %s>' % (self.factoid, self.value)

# vi: set et sta sw=4 ts=4:
