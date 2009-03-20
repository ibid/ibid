from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey, UniqueConstraint, MetaData, Table, DDL, PassiveDefault
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import text
from sqlalchemy.exceptions import OperationalError

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class VersionedSchema(object):
    @classmethod
    def upgrade_schema(cls, sessionmaker):
        session = sessionmaker()
        schema = session.query(Schema).filter(Schema.table==unicode(cls.__table__.name)).first()

        if not schema:
            cls.__table__.create()
            schema = Schema(unicode(cls.__table__.name), cls.schema_version)
            session.save_or_update(schema)
            session.commit()

        elif cls.schema_version > schema.version:
            for version in range(schema.version + 1, cls.schema_version + 1):
                cls.upgrade_schema_to(session, version)
                schema.version = version
                session.save_or_update(schema)
                session.commit()

        session.flush()
        session.close()

    @staticmethod
    def add_column(col):
        sg = col.table.bind.dialect.schemagenerator(col.table.bind.dialect, col.table.bind)
        description = sg.get_column_specification(col)
        DDL('ALTER TABLE %s ADD COLUMN %s;' % (col.table.name, description), bind=col.table.bind).execute()

class Schema(VersionedSchema, Base):
    __table__ = Table('schema', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('table', Unicode(32), unique=True, nullable=False),
        Column('version', Integer, nullable=False),
        useexisting=True)
    
    def __init__(self, table, version=0):
        self.table = table
        self.version = version

    def __repr__(self):
        return '<Schema %s>' % self.table

    @classmethod
    def upgrade_schema(cls, sessionmaker):
        if cls.__table__.name not in cls.__table__.bind.table_names():
            cls.__table__.create()

class Identity(VersionedSchema, Base):
    __table__ = Table('identities', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id')),
        Column('source', Unicode(16), nullable=False),
        Column('identity', Unicode(64), nullable=False),
        Column('created', DateTime, default=func.current_timestamp()),
        UniqueConstraint('source', 'identity'),
        useexisting=True)
    schema_version = 1

    def __init__(self, source, identity, account_id=None):
        self.source = source
        self.identity = identity
        self.account_id = account_id

    def __repr__(self):
        return '<Identity %s on %s>' % (self.identity, self.source)

    @classmethod
    def upgrade_schema_to(cls, session, version):
        raise Exception("Unknown version %i" % version)

class Attribute(VersionedSchema, Base):
    __table__ = Table('account_attributes', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'), nullable=False),
        Column('name', Unicode(32), nullable=False),
        Column('value', Unicode(128), nullable=False),
        UniqueConstraint('account_id', 'name'),
        useexisting=True)
    schema_version = 1

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return '<Attribute %s = %s>' % (self.name, self.value)

    @classmethod
    def upgrade_schema_to(cls, session, version):
        raise Exception("Unknown version %i" % version)

class Credential(VersionedSchema, Base):
    __table__ = Table('credentials', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'), nullable=False),
        Column('source', Unicode(16)),
        Column('method', Unicode(16), nullable=False),
        Column('credential', Unicode(256), nullable=False),
        useexisting=True)
    schema_version = 1

    def __init__(self, method, credential, source=None, account_id=None):
        self.account_id = account_id
        self.source = source
        self.method = method
        self.credential = credential

    @classmethod
    def upgrade_schema_to(cls, session, version):
        raise Exception("Unknown version %i" % version)

class Permission(VersionedSchema, Base):
    __table__ = Table('permissions', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'), nullable=False),
        Column('name', Unicode(16), nullable=False),
        Column('value', Unicode(4), nullable=False),
        UniqueConstraint('account_id', 'name'),
        useexisting=True)
    schema_version = 1


    def __init__(self, name=None, value=None, account_id=None):
        self.account_id = account_id
        self.name = name
        self.value = value

    @classmethod
    def upgrade_schema_to(cls, session, version):
        raise Exception("Unknown version %i" % version)

class Account(VersionedSchema, Base):
    __table__ = Table('accounts', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('username', Unicode(32), unique=True, nullable=False),
        useexisting=True)
    schema_version = 1

    identities = relation(Identity, backref='account')
    attributes = relation(Attribute)
    permissions = relation(Permission)
    credentials = relation(Credential)

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return '<Account %s>' % self.username

    @classmethod
    def upgrade_schema_to(cls, session, version):
        raise Exception("Unknown version %i" % version)

def upgrade_builtin_schemas(sessionmaker):
    for schema in (Schema, Identity, Attribute, Credential, Permission, Account):
        schema.upgrade_schema(sessionmaker)
    session = sessionmaker()

# vi: set et sta sw=4 ts=4:
