from sqlalchemy import Column, Integer, Unicode, DateTime, or_, ForeignKey
from sqlalchemy.orm import relation, backref
from sqlalchemy.ext.declarative import declarative_base

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

class Token(Base):
    __tablename__ = 'auth'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('people.id'))
    source = Column(Unicode)
    method = Column(Unicode)
    token = Column(Unicode)

    def __init__(self, account_id, source, method, token):
        self.account_id = account_id
        self.source = source
        self.method = method
        self.token = token

class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('people.id'))
    permission = Column(Unicode)

    def __init__(self, account_id, permission):
        self.account_id = account_id
        self.permission = permission

class Person(Base):
    __tablename__ = 'people'

    id = Column(Integer, primary_key=True)
    username = Column(Unicode)

    identities = relation(Identity, backref='person')
    attributes = relation(Attribute)
    permissions = relation(Permission)

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return '<Person %s>' % self.username

# vi: set et sta sw=4 ts=4:
