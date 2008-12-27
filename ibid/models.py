from datetime import datetime

from sqlalchemy import Column, Integer, Unicode, DateTime, or_, ForeignKey
from sqlalchemy.orm import relation, backref
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Identity(Base):
    __tablename__ = 'identities'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    source = Column(Unicode)
    identity = Column(Unicode)

    def __init__(self, source, identity, account_id=None):
        self.source = source
        self.identity = identity
        self.account_id = account_id

    def __repr__(self):
        return '<Identity %s on %s>' % (self.identity, self.source)

class Attribute(Base):
    __tablename__ = 'account_attributes'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    name = Column(Unicode)
    value = Column(Unicode)

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return '<Attribute %s = %s>' % (self.name, self.value)

class Authenticator(Base):
    __tablename__ = 'authenticators'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    source = Column(Unicode)
    method = Column(Unicode)
    authenticator = Column(Unicode)

    def __init__(self, account_id, source, method, authenticator):
        self.account_id = account_id
        self.source = source
        self.method = method
        self.authenticator = authenticator

class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    permission = Column(Unicode)

    def __init__(self, account_id, permission):
        self.account_id = account_id
        self.permission = permission

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    username = Column(Unicode)

    identities = relation(Identity, backref='account')
    attributes = relation(Attribute)
    permissions = relation(Permission)

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return '<Account %s>' % self.username

class Sighting(Base):
    __tablename__ = 'seen'

    id = Column(Integer, primary_key=True)
    identity_id = Column(Integer, ForeignKey('identities.id'))
    channel = Column(Unicode)
    saying = Column(Unicode)
    time = Column(DateTime)

    identity = relation('Identity')

    def __init__(self, identity_id, channel, saying):
        self.identity_id = identity_id
        self.channel = channel
        self.saying = saying
        self.time = datetime.now()

# vi: set et sta sw=4 ts=4:
