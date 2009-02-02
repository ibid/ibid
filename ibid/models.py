from datetime import datetime

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey, Boolean, UnicodeText, UniqueConstraint
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Identity(Base):
    __tablename__ = 'identities'
    __table_args__ = (UniqueConstraint('source', 'identity'), {})

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    source = Column(Unicode(16), nullable=False)
    identity = Column(Unicode(64), nullable=False)
    created = Column(DateTime, default=func.current_timestamp())

    def __init__(self, source, identity, account_id=None):
        self.source = source
        self.identity = identity
        self.account_id = account_id

    def __repr__(self):
        return '<Identity %s on %s>' % (self.identity, self.source)

class Attribute(Base):
    __tablename__ = 'account_attributes'
    __table_args__ = (UniqueConstraint('account_id', 'name'), {})
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    name = Column(Unicode(32), nullable=False)
    value = Column(Unicode(128), nullable=False)

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return '<Attribute %s = %s>' % (self.name, self.value)

class Credential(Base):
    __tablename__ = 'credentials'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    source = Column(Unicode(16))
    method = Column(Unicode(16), nullable=False)
    credential = Column(Unicode(256), nullable=False)

    def __init__(self, method, credential, source=None, account_id=None):
        self.account_id = account_id
        self.source = source
        self.method = method
        self.credential = credential

class Permission(Base):
    __tablename__ = 'permissions'
    __table_args__ = (UniqueConstraint('account_id', 'name'), {})

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    name = Column(Unicode(16), nullable=False)
    value = Column(Unicode(4), nullable=False)

    def __init__(self, name=None, value=None, account_id=None):
        self.account_id = account_id
        self.name = name
        self.value = value

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    username = Column(Unicode(32), unique=True, nullable=False)

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
    __table_args__ = (UniqueConstraint('identity_id', 'type'), {})

    id = Column(Integer, primary_key=True)
    identity_id = Column(Integer, ForeignKey('identities.id'), nullable=False)
    type = Column(Unicode(8), nullable=False)
    channel = Column(Unicode(32))
    value = Column(UnicodeText)
    time = Column(DateTime, nullable=False, default=func.current_timestamp())
    count = Column(Integer, nullable=False)

    identity = relation('Identity')

    def __init__(self, identity_id=None, type='message', channel=None, value=None):
        self.identity_id = identity_id
        self.type = type
        self.channel = channel
        self.value = value
        self.count = 0

    def __repr__(self):
        return u'<Sighting %s %s in %s at %s: %s>' % (self.type, self.identity_id, self.channel, self.time, self.value)

class Memo(Base):
    __tablename__ = 'memos'

    id = Column(Integer, primary_key=True)
    frm = Column(Integer, ForeignKey('identities.id'), nullable=False)
    to = Column(Integer, ForeignKey('identities.id'), nullable=False)
    memo = Column(UnicodeText, nullable=False)
    private = Column(Boolean, nullable=False)
    delivered = Column(Boolean, nullable=False)
    time = Column(DateTime, nullable=False, default=func.current_timestamp())

    def __init__(self, frm, to, memo, private=False):
        self.frm = frm
        self.to = to
        self.memo = memo
        self.private = private
        self.delivered = False

Memo.sender = relation(Identity, primaryjoin=Memo.frm==Identity.id)
Memo.recipient = relation(Identity, primaryjoin=Memo.to==Identity.id)

# vi: set et sta sw=4 ts=4:
