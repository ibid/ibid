from sqlalchemy import Column, Integer, Unicode, ForeignKey
from sqlalchemy.orm import relation, backref
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.declarative import declarative_base

import ibid
from ibid.module import Module
from ibid.decorators import *

Base = declarative_base()

class Identity(Base):
    __tablename__ = 'identities'

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'))
    source = Column(Unicode)
    identity = Column(Unicode)

    def __init__(self, source, identity):
        self.source = source
        self.identity = identity

    def __repr__(self):
        return '<Identity %s on %s>' % (self.identity, self.source)

class Attribute(Base):
    __tablename__ = 'person_attributes'
    
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'))
    name = Column(Unicode)
    value = Column(Unicode)

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return '<Attribute %s = %s>' % (self.name, self.value)

class Person(Base):
    __tablename__ = 'people'

    id = Column(Integer, primary_key=True)
    username = Column(Unicode)

    identities = relation(Identity, backref='person')
    attributes = relation(Attribute)

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return '<Person %s>' % self.username

class People(Module):

    @addressed
    @notprocessed
    @match('^\s*add\s+person\s+(.+)\s*$')
    def process(self, event, username):
        session = ibid.databases.ibid()
        person = Person(username)
        session.add(person)
        session.commit()
        session.close()
        event.addresponse(u'Done')

class Identities(Module):

    @addressed
    @notprocessed
    @match('^\s*(I|.+?)\s+(?:is|am)\s+(.+)\s+on\s+(.+)\s*$')
    def process(self, event, username, identity, source):
        session = ibid.databases.ibid()
        if username.upper() == 'I':
            if 'user' not in event:
                event.addresponse(u"I don't know who you are")
                return
            username = event.user

        try:
            person = session.query(Person).filter_by(username=username).one()
        except NoResultFound:
            event.addresponse(u"%s doesn't exist. Please use 'add person' first" % username)
            return

        person.identities.append(Identity(source, identity))
        session.add(person)
        session.commit()
        session.close()
        event.addresponse(u'Done')

class Attributes(Module):

    @addressed
    @notprocessed
    @match(r"^\s*(my|.+?)(?:\'s)?\s+(.+)\s+is\s+(.+)\s*$")
    def process(self, event, username, name, value):
        if username.lower() == 'my':
            if 'user' not in event:
                event.addresponse(u"I don't know who you are")
                return
            username = event.user

        session = ibid.databases.ibid()
        try:
            person = session.query(Person).filter_by(username=username).one()
        except NoResultFound:
            event.addresponse(u"%s doesn't exist. Please use 'add person' first" % username)
            return

        person.attributes.append(Attribute(name, value))
        session.add(person)
        session.commit()
        session.close()
        event.addresponse(u'Done')

class Describe(Module):

    @addressed
    @notprocessed
    @match('^\s*who\s+(?:is|am)\s+(I|.+?)\s*$')
    def process(self, event, username):
        if username.upper() == 'I':
            if 'user' not in event:
                event.addresponse(u"I don't know who you are")
                return
            username = event.user

        session = ibid.databases.ibid()
        try:
            person = session.query(Person).filter_by(username=username).one()
        except NoResultFound:
            event.addresponse(u"%s doesn't exist. Please use 'add person' first" % username)
            return

        event.addresponse(str(person))
        for identity in person.identities:
            event.addresponse(str(identity))
        for attribute in person.attributes:
            event.addresponse(str(attribute))
        session.close()

class Identify(Module):

    def __init__(self, name):
        Module.__init__(self, name)
        self.cache = {}

    @message
    def process(self, event):
        if 'sender_id' in event:
            if event.sender in self.cache:
                event.user = self.cache[event.sender]
                return

            session = ibid.databases.ibid()
            try:
                identity = session.query(Identity).filter_by(source=event.source).filter_by(identity=event.sender_id).one()
            except NoResultFound:
                return

            event.user = identity.person.username
            self.cache[event.sender] = event.user
            session.close()
        
# vi: set et sta sw=4 ts=4:
