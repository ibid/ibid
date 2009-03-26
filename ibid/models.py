import logging

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey, UniqueConstraint, MetaData, Table, PassiveDefault
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
        "Upgrade the table's schema to the latest version."

        table = cls.__table__

        cls.upgrade_session = session = sessionmaker()
        trans = session.begin()

        schema = session.query(Schema).filter(Schema.table==unicode(table.name)).first()

        try:
            if not schema:
                log.info(u"Creating table %s", table.name)
                table.create(bind=session.bind)
                schema = Schema(unicode(table.name), cls.schema_version)
                session.save_or_update(schema)

            elif cls.schema_version > schema.version:
                cls.upgrade_reflected_model = MetaData(session.bind, reflect=True)
                for version in range(schema.version + 1, cls.schema_version + 1):
                    log.info(u"Upgrading table %s to version %i", table.name, version)

                    trans.commit()
                    trans = session.begin()

                    eval('cls.upgrade_schema_to_%i' % version)()

                    schema.version = version
                    session.save_or_update(schema)
                del cls.upgrade_reflected_model

            trans.commit()

        except:
            trans.rollback()
            raise

        session.close()
        del cls.upgrade_session

    @classmethod
    def get_reflected_model(cls, table_name=None):
        "Reflect the given table or the class's __table__"

        return cls.upgrade_reflected_model.tables.get(table_name is None and cls.__table__.name or table_name, None)

    @classmethod
    def add_column(cls, col, table_name=None):
        "Add column col to table. Specify table if name has changed in a more recent version"

        session = cls.upgrade_session
        table = cls.get_reflected_model(table_name)

        log.debug(u"Adding column %s to table %s", col.name, table.name)

        table.append_column(col)

        sg = session.bind.dialect.schemagenerator(session.bind.dialect, session.bind)
        description = sg.get_column_specification(col)

        session.execute('ALTER TABLE %s ADD COLUMN %s;' % (table.name, description))

    @classmethod
    def drop_column(cls, col_name, table_name=None):
        "Drop column col_name from table. Specify table if name has changed in a more recent version"

        session = cls.upgrade_session
        if table_name is None:
            table_name = cls.__table__.name

        log.debug(u"Dropping column %s from table %s", col_name, table_name)

        if session.bind.dialect.name == 'sqlite':
            cls.rebuild_sqlite({col_name: None}, table_name)
        else:
            session.execute('ALTER TABLE %s DROP COLUMN %s;' % (table_name, col_name))

    @classmethod
    def rename_column(cls, col, old_name, table_name=None):
        "Rename column from old_name to Column col. Specify table if name has changed in a more recent version"

        session = cls.upgrade_session
        table = cls.get_reflected_model(table_name)

        log.debug(u"Rename column %s to %s in table %s", old_name, col.name, table.name)

        if session.bind.dialect.name == 'sqlite':
            cls.rebuild_sqlite({old_name: col}, table.name)
        elif session.bind.dialect.name == 'mysql':
            cls.alter_column(col, old_name)
        else:
            session.execute('ALTER TABLE %s RENAME COLUMN %s TO %s;' % (table_name, old_name, col.name))

    @classmethod
    def alter_column(cls, col, old_name=None, length_only=False, table_name=None):
        """Change a column (possibly renaming from old_name) to Column col.
        Specify length_only if the change is simply a change of data-type length.
        Specify table if name has changed in a more recent version."""

        session = cls.upgrade_session
        table = cls.get_reflected_model(table_name)

        log.debug(u"Altering column %s in table %s", col.name, table.name)

        sg = session.bind.dialect.schemagenerator(session.bind.dialect, session.bind)
        description = sg.get_column_specification(col)

        if session.bind.dialect.name == 'sqlite':
            #TODO: Automatically detect length_only
            if length_only:
                # SQLite doesn't enforce value length restrictions, only type changes have a real effect
                return

            cls.rebuild_sqlite({old_name is None and col.name or old_name: col}, table.name)

        elif session.bind.dialect.name == 'mysql':
            session.execute('ALTER TABLE %s CHANGE %s %s %s;'
                % (table.name, old_name is not None and old_name or col.name, col.name, description))

        else:
            if old_name is not None:
                cls.rename_column(col, old_name)
            session.execute('ALTER TABLE %s ALTER COLUMN %s TYPE %s' % (table.name, col.name, description))

    @classmethod
    def rebuild_sqlite(cls, colmap, table_name):
        """SQLite doesn't support modification of table schema - must rebuild the table.
        colmap maps old column names to new Columns (or None for column deletion).
        Only modified columns need to be listed, unchaged columns are carried over automatically.
        Specify table in case name has changed in a more recent version."""

        log.debug(u"Rebuilding SQLite table %s", table_name)

        session = cls.upgrade_session
        table = cls.get_reflected_model(table_name)

        fullcolmap = {}
        for col in table.c:
            if col.name in colmap:
                if colmap[col.name] is not None:
                    fullcolmap[col.name] = colmap[col.name].name
            else:
                fullcolmap[col.name] = col.name

        for old, col in colmap.iteritems():
            del table.c[old]
            if col is not None:
                table.append_column(col)

        session.execute('ALTER TABLE %s RENAME TO %s_old;' % (table.name, table.name))
        table.create()
        session.execute('INSERT INTO %s (%s) SELECT %s FROM %s_old;'
                % (table.name, ", ".join(fullcolmap.values()), ", ".join(fullcolmap.keys()), table.name))
        session.execute('DROP TABLE %s_old;' % table.name)

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
    schema_version = 5

    def __init__(self, source, identity, account_id=None):
        self.source = source
        self.identity = identity
        self.account_id = account_id

    def __repr__(self):
        return '<Identity %s on %s>' % (self.identity, self.source)

    @classmethod
    def upgrade_schema_to_2(cls):
        cls.add_column(Column('foo', Unicode(64)))

    @classmethod
    def upgrade_schema_to_3(cls):
        cls.rename_column(Column('foobar', Unicode(64)), old_name='foo')

    @classmethod
    def upgrade_schema_to_4(cls):
        cls.alter_column(Column('foobar', Unicode(69)))

    @classmethod
    def upgrade_schema_to_5(cls):
        cls.drop_column('foobar')

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
