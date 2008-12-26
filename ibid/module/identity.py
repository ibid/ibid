from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relation, backref
from sqlalchemy.ext.declarative import declarative_base

import ibid
from ibid.module import Module
from ibid.decorators import *

Base = declarative_base()

class Identity(Base):
    __tablename__ = 'identities'

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'))
    source = Column(String)
    identity = Column(String)

    person = relation('Person')

    def __init__(self, source, identity):
        self.source = source
        self.identity = identity

    def __repr__(self):
        return '<Identity %s on %s>' % (self.identity, self.source)

class Attribute(Base):
    __tablename__ = 'person_attributes'
    
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'))
    name = Column(String)
    value = Column(String)

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return '<Attribute %s = %s>' % (self.name, self.value)

class Person(Base):
    __tablename__ = 'people'

    id = Column(Integer, primary_key=True)
    username = Column(String)

    identities = relation(Identity)
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
        event.addresponse(u'Done')

class Identities(Module):

    @addressed
    @notprocessed
    @match('^\s*(I|.+)\s+(?:is|am)\s+(.+)\s+on\s+(.+)\s*$')
    def process(self, event, username, identity, source):
        session = ibid.databases.ibid()
        if username == 'I':
            username = event.user
        person = session.query(Person).filter_by(username=username).one()
        if not person:
            event.addresponse(u"%s doesn't exist. Please use 'add person' first")
        else:
            person.identities.append(Identity(source, identity))
            session.add(person)
            session.commit()
            event.addresponse(u'Done')

class Attributes(Module):

    @addressed
    @notprocessed
    @match(r"^\s*(my|.+?)(?:\'s)?\s+(.+)\s+is\s+(.+)\s*$")
    def process(self, event, username, name, value):
        if username == 'my':
            username = event.user
        session = ibid.databases.ibid()
        person = session.query(Person).filter_by(username=username).one()
        if not person:
            event.addresponse(u"%s doesn't exist. Please use 'add person' first")
        else:
            person.attributes.append(Attribute(name, value))
            session.add(person)
            session.commit()
            event.addresponse(u'Done')

class Describe(Module):

    @addressed
    @notprocessed
    @match('^\s*describe\s+(.+)\s*$')
    def process(self, event, username):
        if username == 'me':
            username = event.user
        session = ibid.databases.ibid()
        person = session.query(Person).filter_by(username=username).one()
        event.addresponse(str(person))
        for identity in person.identities:
            event.addresponse(str(identity))
        for attribute in person.attributes:
            event.addresponse(str(attribute))

class Identify(Module):

    @message
    def process(self, event):
        if 'sender_id' in event:
            session = ibid.databases.ibid()
            identity = session.query(Identity).filter_by(source=event.source).filter_by(identity=event.sender_id).one()
            print identity
            if identity:
                event.user = identity.person.username
        
# vi: set et sta sw=4 ts=4:
