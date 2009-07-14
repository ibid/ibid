import logging
import re

from sqlalchemy import Column, Integer, Unicode, UnicodeText, DateTime, ForeignKey, UniqueConstraint, MetaData, Table, Index, __version__
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.exceptions import InvalidRequestError, OperationalError

if __version__ < '0.5':
    NoResultFound = InvalidRequestError
else:
    from sqlalchemy.orm.exc import NoResultFound

metadata = MetaData()
Base = declarative_base(metadata=metadata)
log = logging.getLogger('ibid.models')

class VersionedSchema(object):
    """For an initial table schema, set
    table.versioned_schema = VersionedSchema(__table__, 1)
    Table creation (upgrading to version 1) is implicitly supported.

    When you have upgrades to the schema, instead of using VersionedSchema
    directly, derive from it and include your own upgrade_x_to_y(self) methods,
    where y = x + 1
    
    In the upgrade methods, you can call the helper functions:
    add_column, drop_column, rename_column, alter_column
    They try to do the correct thing in most situations, including rebuilding
    tables in SQLite, which doesn't actually support dropping/altering columns.
    For column parameters, while you can point to columns in the table
    definition, it is better style to repeat the Column() specification as the
    column might be altered in a future version.
    """
    foreign_key_re = re.compile(r'^FOREIGN KEY\(.*?\) (REFERENCES .*)$', re.I)

    def __init__(self, table, version):
        self.table = table
        self.version = version

    def is_up_to_date(self, session):
        "Is the table in the database up to date with the schema?"

        if not session.bind.has_table(self.table.name):
            return False

        try:
            schema = session.query(Schema).filter(Schema.table==unicode(self.table.name)).one()
            return schema.version == self.version
        except NoResultFound:
            return False

    def upgrade_schema(self, sessionmaker):
        "Upgrade the table's schema to the latest version."

        for fk in self.table.foreign_keys:
            dependancy = fk.target_fullname.split('.')[0]
            log.debug("Upgrading table %s before %s", dependancy, self.table.name)
            metadata.tables[dependancy].versioned_schema.upgrade_schema(sessionmaker)

        self.upgrade_session = session = sessionmaker()
        self.upgrade_reflected_model = MetaData(session.bind, reflect=True)

        if self.table.name == 'schema':
            if not session.bind.has_table(self.table.name):
                metadata.bind = session.bind
                self._create_table()

                schema = Schema(unicode(self.table.name), self.version)
                session.save_or_update(schema)
                return
            Schema.__table__ = self._get_reflected_model()

        schema = session.query(Schema).filter(Schema.table==unicode(self.table.name)).first()

        try:
            if not schema:
                log.info(u"Creating table %s", self.table.name)

                self._create_table()

                schema = Schema(unicode(self.table.name), self.version)
                session.save_or_update(schema)

            elif self.version > schema.version:
                for version in range(schema.version + 1, self.version + 1):
                    log.info(u"Upgrading table %s to version %i", self.table.name, version)

                    session.commit()

                    getattr(self, 'upgrade_%i_to_%i' % (version - 1, version))()

                    schema.version = version
                    session.save_or_update(schema)
                del self.upgrade_reflected_model

            session.commit()

        except:
            session.rollback()
            raise

        session.close()
        del self.upgrade_session

    def _index_name(self, col):
        """
        We'd like to not duplicate an existing index so try to abide by the local customs
        """
        session = self.upgrade_session

        if session.bind.engine.name == 'sqlite':
            return 'ix_%s_%s' % (self.table.name, col.name)
        elif session.bind.engine.name == 'postgres':
            return '%s_%s_key' % (self.table.name, col.name)
        elif session.bind.engine.name == 'mysql':
            return col.name

        log.warning(u"Unknown database type, %s, you may end up with duplicate indices"
                % session.bind.engine.name)
        return 'ix_%s_%s' % (self.table.name, col.name)

    def _mysql_constraint_createstring(self, constraint):
        """Generate the description of a constraint for insertion into a CREATE string"""
        return ', '.join(
            (isinstance(column.type, UnicodeText)
                    and '"%(name)s"(%(length)i)'
                    or '"%(name)s"') % {
                'name': column.name,
                'length': column.info.get('ibid_mysql_index_length', 8),
            } for column in constraint.columns
        )

    def _create_table(self):
        """Check that the table is in a suitable form for all DBs, before creating.
        Yes, SQLAlchemy's abstractions are leaky enough that you have to do this"""

        session = self.upgrade_session
        indices = []
        old_indexes = list(self.table.indexes)
        old_constraints = list(self.table.constraints)

        for column in self.table.c:
            if column.unique and not column.index:
                raise Exception(u"Column %s.%s is unique but not indexed. "
                    u"SQLite doesn't like such things, so please be nice and don't do that."
                    % (self.table.name, self.column.name))

        # Strip out Indexes and Constraints that SQLAlchemy can't create by itself
        if session.bind.engine.name == 'mysql':
            for type, old_list in (
                    ('constraints', old_constraints),
                    ('indexes', old_indexes)):
                for constraint in old_list:
                    if [True for column in constraint.columns if isinstance(column.type, UnicodeText)]:
                        indices.append((isinstance(constraint, UniqueConstraint),
                            self._mysql_constraint_createstring(constraint)))

                        getattr(self.table, type).remove(constraint)

        self.table.create(bind=session.bind)

        if session.bind.engine.name == 'mysql':
            for constraint in old_constraints:
                if constraint not in self.table.constraints:
                    self.table.constraints.add(constraint)

            for index in old_indexes:
                if index not in self.table.indexes:
                    self.table.indexes.add(index)

            for unique, columnspec in indices:
                session.execute('ALTER TABLE "%s" ADD %s INDEX (%s);' % (
                    self.table.name, unique and 'UNIQUE' or '', columnspec))

    def _get_reflected_model(self):
        "Get a reflected table from the current DB's schema"

        return self.upgrade_reflected_model.tables.get(self.table.name, None)

    def add_column(self, col):
        "Add column col to table"

        session = self.upgrade_session
        table = self._get_reflected_model()

        log.debug(u"Adding column %s to table %s", col.name, table.name)

        constraints = table.constraints.copy()
        table.append_column(col)
        constraints = table.constraints - constraints

        sg = session.bind.dialect.schemagenerator(session.bind.dialect, session.bind)
        description = sg.get_column_specification(col)

        for constraint in constraints:
            sg.traverse_single(constraint)

        constraints = []
        for constraint in [x.strip() for x in sg.buffer.getvalue().split(',')]:
            m = self.foreign_key_re.match(constraint)
            if m:
                constraints.append(m.group(1))
            else:
                constraints.append(constraint)

        session.execute('ALTER TABLE "%s" ADD COLUMN %s %s;' % (table.name, description, " ".join(constraints)))

    def add_index(self, col, unique=False):
        "Add an index to the table"

        try:
            Index(self._index_name(col), col, unique=unique) \
                    .create(bind=self.upgrade_session.bind)
        except OperationalError, e:
            if u'Duplicate' not in unicode(e):
                raise

    def drop_column(self, col_name):
        "Drop column col_name from table"

        session = self.upgrade_session

        log.debug(u"Dropping column %s from table %s", col_name, self.table.name)

        if session.bind.engine.name == 'sqlite':
            self._rebuild_sqlite({col_name: None})
        else:
            session.execute('ALTER TABLE "%s" DROP COLUMN "%s";' % (self.table.name, col_name))

    def rename_column(self, col, old_name):
        "Rename column from old_name to Column col"

        session = self.upgrade_session
        table = self._get_reflected_model()

        log.debug(u"Rename column %s to %s in table %s", old_name, col.name, table.name)

        if session.bind.engine.name == 'sqlite':
            self._rebuild_sqlite({old_name: col})
        elif session.bind.engine.name == 'mysql':
            self.alter_column(col, old_name)
        else:
            session.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s";' % (table.name, old_name, col.name))

    def alter_column(self, col, old_name=None):
        """Change a column (possibly renaming from old_name) to Column col."""

        session = self.upgrade_session
        table = self._get_reflected_model()

        log.debug(u"Altering column %s in table %s", col.name, table.name)

        sg = session.bind.dialect.schemagenerator(session.bind.dialect, session.bind)
        description = sg.get_column_specification(col)
        old_col = table.c[old_name or col.name]

        if session.bind.engine.name == 'sqlite':
            if (isinstance(col.type, (UnicodeText, Unicode))
                        and isinstance(old_col.type, (UnicodeText, Unicode))
                    ) or (isinstance(col.type, Integer)
                        and isinstance(old_col.type, (Integer))):
                # SQLite doesn't enforce value length restrictions
                # only type changes have a real effect
                return

            self._rebuild_sqlite({old_name is None and col.name or old_name: col})

        elif session.bind.engine.name == 'mysql':
            # Special handling for columns of TEXT type, because SQLAlchemy
            # can't create indexes for them
            recreate = []
            if isinstance(col.type, UnicodeText) or isinstance(old_col.type, UnicodeText):
                for type in (table.constraints, table.indexes):
                    for constraint in list(type):
                        if [True for column in constraint.columns if old_col.name == column.name]:
                            constraint.drop()

                            constraint.columns = [
                                    (old_col.name != column.name) and column or col
                                    for column in constraint.columns
                            ]
                            recreate.append((isinstance(constraint, UniqueConstraint),
                                self._mysql_constraint_createstring(constraint)))
            
            session.execute('ALTER TABLE "%s" CHANGE "%s" %s;'
                % (table.name, old_col.name, description))

            for unique, columnspec in recreate:
                session.execute('ALTER TABLE "%s" ADD %s INDEX (%s);' % (
                    self.table.name, unique and 'UNIQUE' or '', columnspec))

        else:
            if old_name is not None:
                self.rename_column(col, old_name)
            session.execute('ALTER TABLE "%s" ALTER COLUMN "%s" TYPE %s'
                % (table.name, col.name, description.split(" ", 1)[1]))

    def _rebuild_sqlite(self, colmap):
        """SQLite doesn't support modification of table schema - must rebuild the table.
        colmap maps old column names to new Columns (or None for column deletion).
        Only modified columns need to be listed, unchaged columns are carried over automatically.
        Specify table in case name has changed in a more recent version."""

        session = self.upgrade_session
        table = self._get_reflected_model()

        log.debug(u"Rebuilding SQLite table %s", table.name)

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

        session.execute('ALTER TABLE "%s" RENAME TO "%s_old";' % (table.name, table.name))
        table.create()
        session.execute('INSERT INTO "%s" ("%s") SELECT "%s" FROM "%s_old";'
                % (table.name, '", "'.join(fullcolmap.values()), '", "'.join(fullcolmap.keys()), table.name))
        session.execute('DROP TABLE "%s_old";' % table.name)

class Schema(Base):
    __table__ = Table('schema', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('table', Unicode(32), unique=True, nullable=False, index=True),
        Column('version', Integer, nullable=False),
        useexisting=True)

    class SchemaSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.table, unique=True)

    __table__.versioned_schema = SchemaSchema(__table__, 2)
    
    def __init__(self, table, version=0):
        self.table = table
        self.version = version

    def __repr__(self):
        return '<Schema %s>' % self.table

class Identity(Base):
    __table__ = Table('identities', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'), index=True),
        Column('source', Unicode(32), nullable=False, index=True),
        Column('identity', UnicodeText, nullable=False, index=True),
        Column('created', DateTime, default=func.current_timestamp()),
        UniqueConstraint('source', 'identity'),
        useexisting=True)

    class IdentitySchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.account_id)
            self.add_index(self.table.c.source)
            self.add_index(self.table.c.identity)

        def upgrade_2_to_3(self):
            self.alter_column(Column('source', Unicode(32), nullable=False, index=True))
            self.alter_column(Column('identity', UnicodeText, nullable=False, index=True))

    __table__.versioned_schema = IdentitySchema(__table__, 3)

    def __init__(self, source, identity, account_id=None):
        self.source = source
        self.identity = identity
        self.account_id = account_id

    def __repr__(self):
        return '<Identity %s on %s>' % (self.identity, self.source)

class Attribute(Base):
    __table__ = Table('account_attributes', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'), nullable=False, index=True),
        Column('name', Unicode(32), nullable=False, index=True),
        Column('value', UnicodeText, nullable=False),
        UniqueConstraint('account_id', 'name'),
        useexisting=True)

    class AttributeSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.account_id)
            self.add_index(self.table.c.name)
        def upgrade_2_to_3(self):
            self.alter_column(Column('value', UnicodeText, nullable=False))

    __table__.versioned_schema = AttributeSchema(__table__, 3)

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return '<Attribute %s = %s>' % (self.name, self.value)

class Credential(Base):
    __table__ = Table('credentials', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'), nullable=False, index=True),
        Column('source', Unicode(32), index=True),
        Column('method', Unicode(16), nullable=False, index=True),
        Column('credential', UnicodeText, nullable=False),
        useexisting=True)

    class CredentialSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.account_id)
            self.add_index(self.table.c.source)
            self.add_index(self.table.c.method)
        def upgrade_2_to_3(self):
            self.alter_column(Column('source', Unicode(32), index=True))
            self.alter_column(Column('credential', UnicodeText, nullable=False))

    __table__.versioned_schema = CredentialSchema(__table__, 3)

    def __init__(self, method, credential, source=None, account_id=None):
        self.account_id = account_id
        self.source = source
        self.method = method
        self.credential = credential

class Permission(Base):
    __table__ = Table('permissions', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('account_id', Integer, ForeignKey('accounts.id'), nullable=False, index=True),
        Column('name', Unicode(16), nullable=False, index=True),
        Column('value', Unicode(4), nullable=False),
        UniqueConstraint('account_id', 'name'),
        useexisting=True)

    class PermissionSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.account_id)
            self.add_index(self.table.c.name)

    __table__.versioned_schema = PermissionSchema(__table__, 2)

    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value

class Account(Base):
    __table__ = Table('accounts', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('username', Unicode(32), unique=True, nullable=False, index=True),
        useexisting=True)

    class AccountSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.username, unique=True)

    __table__.versioned_schema = AccountSchema(__table__, 2)

    identities = relation(Identity, backref='account', cascade='all')
    attributes = relation(Attribute, cascade='all, delete-orphan')
    permissions = relation(Permission, cascade='all, delete-orphan')
    credentials = relation(Credential, cascade='all, delete-orphan')

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return '<Account %s>' % self.username

def check_schema_versions(sessionmaker):
    """Pass through all tables, log out of date ones,
    and except if not all up to date"""

    session = sessionmaker()
    upgrades = []
    for table in metadata.tables.itervalues():
        if not hasattr(table, 'versioned_schema'):
            log.error("Table %s is not versioned.", table.name)
            continue

        if not table.versioned_schema.is_up_to_date(session):
            upgrades.append(table.name)

    if not upgrades:
        return

    raise Exception(u"Tables %s are out of date. Run ibid-setup" % u", ".join(upgrades))

def upgrade_schemas(sessionmaker):
    "Pass through all tables and update schemas"

    # Make sure schema table is created first
    metadata.tables['schema'].versioned_schema.upgrade_schema(sessionmaker)

    for table in metadata.tables.itervalues():
        if not hasattr(table, 'versioned_schema'):
            log.error("Table %s is not versioned.", table.name)
            continue

        table.versioned_schema.upgrade_schema(sessionmaker)

# vi: set et sta sw=4 ts=4:
