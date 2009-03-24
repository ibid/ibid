import logging

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey, UniqueConstraint, MetaData, Table, DDL, PassiveDefault
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import text
from sqlalchemy.exceptions import OperationalError

metadata = MetaData()
Base = declarative_base(metadata=metadata)
log = logging.getLogger('ibid.models')

class VersionedSchema(object):
    @classmethod
    def upgrade_schema(cls, sessionmaker):
        session = sessionmaker()
        schema = session.query(Schema).filter(Schema.table==unicode(cls.__table__.name)).first()

        if not schema:
            log.info(u"Creating table %s", cls.__table__.name)
            metadata.bind = session.bind
            cls.__table__.create()
            schema = Schema(unicode(cls.__table__.name), cls.schema_version)
            session.save_or_update(schema)
            session.commit()

        elif cls.schema_version > schema.version:
            for version in range(schema.version + 1, cls.schema_version + 1):
                log.info(u"Upgrading table %s to version %i", cls.__table__.name, version)
                metadata.bind = session.bind
                eval('cls.upgrade_schema_to_%i' % version)()
                schema.version = version
                session.save_or_update(schema)
                session.commit()

        session.flush()
        session.close()

    @staticmethod
    def add_column(col):
        log.debug(u"Adding column %s to table %s", col.name, col.table.name)
        sg = col.table.bind.dialect.schemagenerator(col.table.bind.dialect, col.table.bind)
        description = sg.get_column_specification(col)
        DDL('ALTER TABLE %s ADD COLUMN %s;' % (col.table.name, description), bind=col.table.bind).execute()

    @staticmethod
    def drop_column(table, col_name):
        log.debug(u"Dropping column %s from table %s", col_name, table.name)
        if table.bind.dialect.name == 'sqlite':
            VersionedSchema.rebuild_sqlite(table, colmap={col_name: None})
        else:
            DDL('ALTER TABLE %s DROP COLUMN %s;' % (table.name, col_name), bind=table.bind).execute()

    @staticmethod
    def rename_column(col, old_name):
        log.debug(u"Rename column %s to %s in table %s", old_name, col.name, col.table.name)
        if col.table.bind.dialect.name == 'sqlite':
            VersionedSchema.rebuild_sqlite(col.table, colmap={old_name: col.name})
        elif col.table.bind.dialect.name == 'mysql':
            VersionedSchema.alter_column(col, old_name is None and col.name or old_name)
        else:
            DDL('ALTER TABLE %s RENAME COLUMN %s TO %s;' % (col.table.name, old_name, col.name), bind=col.table.bind).execute()

    @staticmethod
    def alter_column(col, old_name=None, length_only=False):
        log.debug(u"Altering column %s in table %s", col.name, col.table.name)
        sg = col.table.bind.dialect.schemagenerator(col.table.bind.dialect, col.table.bind)
        description = sg.get_column_specification(col)

        if col.table.bind.dialect.name == 'sqlite':
            if length_only:
                # SQLite doesn't enforce value length restrictions, only type changes have a real effect
                return
            colmap = {}
            if old_name is not None:
                colmap[old_name] = col.name
            VersionedSchema.rebuild_sqlite(colmap=colmap)

        elif col.table.bind.dialect.name == 'mysql':
            DDL('ALTER TABLE %s CHANGE %s %s %s;'
                    % (col.table.name, old_name is not None and old_name or col.table.name, col.name, description),
                    bind=col.table.bind).execute()

        else:
            if old_name is not None:
                VersionedSchema.rename_column(col, old_name)
            DDL('ALTER TABLE %s ALTER COLUMN %s TYPE %s' % (col.table.name, col.name, description),
                    bind=col.table.bind).execute()

    @staticmethod
    def rebuild_sqlite(table, colmap):
        """SQLite doesn't support modification of table schema - must rebuild the table.
        colmap maps hold column names to new ones (or None)"""

        log.debug(u"Rebuilding SQLite table %s", table.name)

        fullcolmap = {}
        for col in table.c:
            if col.name in colmap:
                fullcolmap[col.name] = colmap[col.name]
            else:
                fullcolmap[col.name] = col.name

        DDL('ALTER TABLE %s RENAME TO %s_old;' % (table.name, table.name), bind=table.bind).execute()
        table.create()
        table.bind.execute('INSERT INTO %s (%s) SELECT %s FROM %s_old;'
                % (table.name, ", ".join(fullcolmap.values()), ", ".join(fullcolmap.keys()), table.name))
        DDL('DROP TABLE %s_old;')

    @staticmethod
    def rename_table(table, old_name):
        log.debug(u"Renaming table %s to %s", old_name, table.name)
        DDL('ALTER TABLE %s RENAME TO %s;' % (old_name, table.name), bind=table.bind).execute()

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
        session = sessionmaker()
        if not session.bind.has_table(cls.__table__.name):
            metadata.bind = session.bind
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

def upgrade_builtin_schemas(sessionmaker):
    for schema in (Schema, Identity, Attribute, Credential, Permission, Account):
        schema.upgrade_schema(sessionmaker)
    session = sessionmaker()

# vi: set et sta sw=4 ts=4:
