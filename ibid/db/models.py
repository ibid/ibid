from datetime import datetime

from ibid.db.types import IbidUnicode, IbidUnicodeText, Integer, DateTime
from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relation
from ibid.db import Base
from ibid.db.versioned_schema import VersionedSchema

class Schema(Base):
    __table__ = Table('schema', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('table', IbidUnicode(32), unique=True, nullable=False,
               index=True),
        Column('version', Integer, nullable=False),
        useexisting=True)

    class SchemaSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.table)
        def upgrade_2_to_3(self):
            self.drop_index(self.table.c.table)
            self.alter_column(Column('table', IbidUnicode(32), unique=True,
                              nullable=False, index=True), force_rebuild=True)
            self.add_index(self.table.c.table)

    __table__.versioned_schema = SchemaSchema(__table__, 3)

    def __init__(self, table, version=0):
        self.table = table
        self.version = version

    def __repr__(self):
        return '<Schema %s>' % self.table

class Identity(Base):
    __table__ = Table('identities', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'), index=True),
        Column('source', IbidUnicode(32, case_insensitive=True),
               nullable=False, index=True),
        Column('identity', IbidUnicodeText(32, case_insensitive=True),
               nullable=False, index=True),
        Column('created', DateTime),
        UniqueConstraint('source', 'identity'),
        useexisting=True)

    class IdentitySchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.account_id)
            self.add_index(self.table.c.source)
            self.add_index(self.table.c.identity)

        def upgrade_2_to_3(self):
            self.alter_column(Column('source', IbidUnicode(32),
                                     nullable=False, index=True))
            self.alter_column(Column('identity', IbidUnicodeText,
                                     nullable=False, index=True))
        def upgrade_3_to_4(self):
            self.drop_index(self.table.c.source)
            self.drop_index(self.table.c.identity)
            self.alter_column(Column('source',
                                     IbidUnicode(32, case_insensitive=True),
                                     nullable=False, index=True),
                              force_rebuild=True)
            self.alter_column(Column('identity',
                                     IbidUnicodeText(32, case_insensitive=True),
                                     nullable=False, index=True),
                              force_rebuild=True)
            self.add_index(self.table.c.source)
            self.add_index(self.table.c.identity)

    __table__.versioned_schema = IdentitySchema(__table__, 4)

    def __init__(self, source, identity, account_id=None):
        self.source = source
        self.identity = identity
        self.account_id = account_id
        self.created = datetime.utcnow()

    def __repr__(self):
        return '<Identity %s on %s>' % (self.identity, self.source)

class Attribute(Base):
    __table__ = Table('account_attributes', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'),
               nullable=False, index=True),
        Column('name', IbidUnicode(32, case_insensitive=True),
               nullable=False, index=True),
        Column('value', IbidUnicodeText, nullable=False),
        UniqueConstraint('account_id', 'name'),
        useexisting=True)

    class AttributeSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.account_id)
            self.add_index(self.table.c.name)
        def upgrade_2_to_3(self):
            self.alter_column(Column('value', IbidUnicodeText, nullable=False))
        def upgrade_3_to_4(self):
            self.drop_index(self.table.c.name)
            self.alter_column(Column('name',
                                     IbidUnicode(32, case_insensitive=True),
                                     nullable=False, index=True),
                              force_rebuild=True)
            self.alter_column(Column('value', IbidUnicodeText, nullable=False),
                              force_rebuild=True)
            self.add_index(self.table.c.name)

    __table__.versioned_schema = AttributeSchema(__table__, 4)

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return '<Attribute %s = %s>' % (self.name, self.value)

class Credential(Base):
    __table__ = Table('credentials', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'),
               nullable=False, index=True),
        Column('source', IbidUnicode(32, case_insensitive=True), index=True),
        Column('method', IbidUnicode(16, case_insensitive=True),
               nullable=False, index=True),
        Column('credential', IbidUnicodeText, nullable=False),
        useexisting=True)

    class CredentialSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.account_id)
            self.add_index(self.table.c.source)
            self.add_index(self.table.c.method)
        def upgrade_2_to_3(self):
            self.alter_column(Column('source', IbidUnicode(32), index=True))
            self.alter_column(Column('credential',
                                     IbidUnicodeText, nullable=False))
        def upgrade_3_to_4(self):
            self.drop_index(self.table.c.source)
            self.drop_index(self.table.c.method)
            self.alter_column(Column('source',
                                     IbidUnicode(32, case_insensitive=True),
                                     index=True), force_rebuild=True)
            self.alter_column(Column('method',
                                     IbidUnicode(16, case_insensitive=True),
                                     nullable=False, index=True),
                              force_rebuild=True)
            self.alter_column(Column('credential', IbidUnicodeText,
                                     nullable=False), force_rebuild=True)
            self.add_index(self.table.c.source)
            self.add_index(self.table.c.method)

    __table__.versioned_schema = CredentialSchema(__table__, 4)

    def __init__(self, method, credential, source=None, account_id=None):
        self.account_id = account_id
        self.source = source
        self.method = method
        self.credential = credential

class Permission(Base):
    __table__ = Table('permissions', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'),
               nullable=False, index=True),
        Column('name', IbidUnicode(16, case_insensitive=True),
               nullable=False, index=True),
        Column('value', IbidUnicode(4, case_insensitive=True), nullable=False),
        UniqueConstraint('account_id', 'name'),
        useexisting=True)

    class PermissionSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.account_id)
            self.add_index(self.table.c.name)
        def upgrade_2_to_3(self):
            self.drop_index(self.table.c.name)
            self.alter_column(Column('name',
                                     IbidUnicode(16, case_insensitive=True),
                                     index=True), force_rebuild=True)
            self.alter_column(Column('value',
                                     IbidUnicode(4, case_insensitive=True),
                                     nullable=False, index=True),
                              force_rebuild=True)
            self.add_index(self.table.c.name)

    __table__.versioned_schema = PermissionSchema(__table__, 3)

    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value

class Account(Base):
    __table__ = Table('accounts', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('username', IbidUnicode(32, case_insensitive=True),
               unique=True, nullable=False, index=True),
        useexisting=True)

    class AccountSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.username)
        def upgrade_2_to_3(self):
            self.drop_index(self.table.c.username)
            self.alter_column(Column('username',
                                     IbidUnicode(32, case_insensitive=True),
                                     unique=True, nullable=False, index=True),
                              force_rebuild=True)
            self.add_index(self.table.c.username)

    __table__.versioned_schema = AccountSchema(__table__, 3)

    identities = relation(Identity, backref='account')
    attributes = relation(Attribute, cascade='all, delete-orphan')
    permissions = relation(Permission, cascade='all, delete-orphan')
    credentials = relation(Credential, cascade='all, delete-orphan')

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return '<Account %s>' % self.username

# vi: set et sta sw=4 ts=4:
