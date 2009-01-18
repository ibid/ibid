from datetime import datetime

from sqlalchemy import Column, Integer, Unicode, DateTime, or_, ForeignKey, Boolean, UnicodeText
from sqlalchemy.orm import relation, backref
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Identity(Base):
    __tablename__ = 'identities'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    source = Column(Unicode(16))
    identity = Column(Unicode(64))

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
    name = Column(Unicode(16))
    value = Column(Unicode(64))

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return '<Attribute %s = %s>' % (self.name, self.value)

class Credential(Base):
    __tablename__ = 'credentials'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    source = Column(Unicode(16))
    method = Column(Unicode(16))
    credential = Column(Unicode(256))

    def __init__(self, method, credential, source=None, account_id=None):
        self.account_id = account_id
        self.source = source
        self.method = method
        self.credential = credential

class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    name = Column(Unicode(16))
    value = Column(Unicode(4))

    def __init__(self, name=None, value=None, account_id=None):
        self.account_id = account_id
        self.name = name
        self.value = value

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    username = Column(Unicode(32))

    identities = relation(Identity, backref='account')
    attributes = relation(Attribute)
    permissions = relation(Permission)
    credentials = relation(Credential)

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return '<Account %s>' % self.username

class Sighting(Base):
    __tablename__ = 'seen'

    id = Column(Integer, primary_key=True)
    identity_id = Column(Integer, ForeignKey('identities.id'))
    type = Column(Unicode(8))
    channel = Column(Unicode(32))
    value = Column(UnicodeText)
    time = Column(DateTime)
    count = Column(Integer)

    identity = relation('Identity')

    def __init__(self, identity_id=None, channel=None, value=None):
        self.identity_id = identity_id
        self.channel = channel
        self.value = value
        self.time = datetime.now()
        self.count = 0

class Memo(Base):
    __tablename__ = 'memos'

    id = Column(Integer, primary_key=True)
    frm = Column(Integer, ForeignKey('identities.id'))
    to = Column(Integer, ForeignKey('identities.id'))
    memo = Column(UnicodeText)
    private = Column(Boolean)
    delivered = Column(Boolean)
    time = Column(DateTime)

    def __init__(self, frm, to, memo, private=False):
        self.frm = frm
        self.to = to
        self.memo = memo
        self.private = private
        self.delivered = False
        self.time = datetime.now()

Memo.sender = relation(Identity, primaryjoin=Memo.frm==Identity.id)
Memo.recipient = relation(Identity, primaryjoin=Memo.to==Identity.id)

# vi: set et sta sw=4 ts=4:
