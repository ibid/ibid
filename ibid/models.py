from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey, UniqueConstraint, MetaData, Table
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class Identity(Base):
    __table__ = Table('identities', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('account_id', Integer, ForeignKey('accounts.id')),
    Column('source', Unicode(16), nullable=False),
    Column('identity', Unicode(64), nullable=False),
    Column('created', DateTime, default=func.current_timestamp()),
    UniqueConstraint('source', 'identity'),
    useexisting=True)

    def __init__(self, source, identity, account_id=None):
        self.source = source
        self.identity = identity
        self.account_id = account_id

    def __repr__(self):
        return '<Identity %s on %s>' % (self.identity, self.source)

class Attribute(Base):
    __table__ = Table('account_attributes', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('account_id', Integer, ForeignKey('accounts.id'), nullable=False),
    Column('name', Unicode(32), nullable=False),
    Column('value', Unicode(128), nullable=False),
    UniqueConstraint('account_id', 'name'),
    useexisting=True)

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return '<Attribute %s = %s>' % (self.name, self.value)

class Credential(Base):
    __table__ = Table('credentials', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('account_id', Integer, ForeignKey('accounts.id'), nullable=False),
    Column('source', Unicode(16)),
    Column('method', Unicode(16), nullable=False),
    Column('credential', Unicode(256), nullable=False),
    useexisting=True)

    def __init__(self, method, credential, source=None, account_id=None):
        self.account_id = account_id
        self.source = source
        self.method = method
        self.credential = credential

class Permission(Base):
    __table__ = Table('permissions', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('account_id', Integer, ForeignKey('accounts.id'), nullable=False),
    Column('name', Unicode(16), nullable=False),
    Column('value', Unicode(4), nullable=False),
    UniqueConstraint('account_id', 'name'),
    useexisting=True)


    def __init__(self, name=None, value=None, account_id=None):
        self.account_id = account_id
        self.name = name
        self.value = value

class Account(Base):
    __table__ = Table('accounts', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('username', Unicode(32), unique=True, nullable=False),
    useexisting=True)

    identities = relation(Identity, backref='account')
    attributes = relation(Attribute)
    permissions = relation(Permission)
    credentials = relation(Credential)

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return '<Account %s>' % self.username

# vi: set et sta sw=4 ts=4:
