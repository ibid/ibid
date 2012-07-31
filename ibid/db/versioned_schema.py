# Copyright (c) 2009-2010, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import logging
import re

from sqlalchemy import Column, Index, CheckConstraint, UniqueConstraint, \
                       MetaData, __version__ as _sqlalchemy_version
from sqlalchemy.exc import InvalidRequestError, OperationalError, \
                                  ProgrammingError, InternalError
from sqlalchemy.orm.exc import NoResultFound

from ibid.db.types import Integer, IbidUnicodeText, IbidUnicode

from ibid.db import metadata

log = logging.getLogger('ibid.db.versioned_schema')

if _sqlalchemy_version < '0.6':
    pg_engine = 'postgres'
else:
    pg_engine = 'postgresql'

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

    def __init__(self, table, version):
        self.table = table
        self.version = version

    def is_up_to_date(self, session):
        "Is the table in the database up to date with the schema?"

        from ibid.db.models import Schema

        if not session.bind.has_table(self.table.name):
            return False

        try:
            schema = session.query(Schema) \
                    .filter_by(table=unicode(self.table.name)).one()
            return schema.version == self.version
        except NoResultFound:
            return False

    def upgrade_schema(self, sessionmaker):
        "Upgrade the table's schema to the latest version."

        from ibid.db.models import Schema

        for fk in self.table.foreign_keys:
            dependency = fk.target_fullname.split('.')[0]
            log.debug("Upgrading table %s before %s",
                    dependency, self.table.name)
            metadata.tables[dependency].versioned_schema \
                    .upgrade_schema(sessionmaker)

        self.upgrade_session = session = sessionmaker()
        self.upgrade_reflected_model = MetaData(session.bind, reflect=True)

        if self.table.name == 'schema':
            if not session.bind.has_table(self.table.name):
                metadata.bind = session.bind
                self._create_table()

                schema = Schema(unicode(self.table.name), self.version)
                session.add(schema)
                return
            Schema.__table__ = self._get_reflected_model()

        schema = session.query(Schema) \
                .filter_by(table=unicode(self.table.name)).first()

        try:
            if not schema:
                log.info(u"Creating table %s", self.table.name)

                self._create_table()

                schema = Schema(unicode(self.table.name), self.version)
                session.add(schema)

            elif self.version > schema.version:
                for version in range(schema.version + 1, self.version + 1):
                    log.info(u"Upgrading table %s to version %i",
                            self.table.name, version)

                    session.commit()

                    getattr(self, 'upgrade_%i_to_%i' % (version - 1, version))()

                    schema.version = version
                    session.add(schema)

                    self.upgrade_reflected_model = \
                            MetaData(session.bind, reflect=True)

            session.commit()

        except:
            session.rollback()
            raise

        session.close()
        del self.upgrade_session

    def _index_name(self, col):
        """
        We'd like not to duplicate an existing index so try to abide by the
        local customs
        """
        session = self.upgrade_session

        if session.bind.engine.name == 'sqlite':
            return 'ix_%s_%s' % (self.table.name, col.name)
        elif session.bind.engine.name == pg_engine:
            return '%s_%s_key' % (self.table.name, col.name)
        elif session.bind.engine.name == 'mysql':
            return col.name

        log.warning(u"Unknown database type, %s, you may end up with "
                u"duplicate indices" % session.bind.engine.name)
        return 'ix_%s_%s' % (self.table.name, col.name)

    def _mysql_constraint_createstring(self, constraint):
        """
        Generate the description of a constraint for insertion into a CREATE
        string
        """
        names = []
        for column in constraint.columns:
            if isinstance(column.type, IbidUnicodeText):
                names.append('"%s"(%i)'
                             % (column.name, column.type.index_length))
            else:
                names.append(column.name)

        return ', '.join(names)

    def _create_table(self):
        """
        Check that the table is in a suitable form for all DBs, before
        creating. Yes, SQLAlchemy's abstractions are leaky enough that you have
        to do this
        """
        session = self.upgrade_session
        indices = []
        old_indexes = list(self.table.indexes)
        old_constraints = list(self.table.constraints)

        for column in self.table.c:
            if column.unique and not column.index:
                raise Exception(u"Column %s.%s is unique but not indexed. "
                    u"SQLite doesn't like such things, "
                    u"so please be nice and don't do that."
                    % (self.table.name, column.name))

        # Strip out Indexes and Constraints that SQLAlchemy can't create by
        # itself
        if session.bind.engine.name == 'mysql':
            for type, old_list in (
                    ('constraints', old_constraints),
                    ('indexes', old_indexes)):
                for constraint in old_list:
                    if isinstance(constraint, CheckConstraint):
                        continue
                    if any(True for column in constraint.columns
                            if isinstance(column.type, IbidUnicodeText)):
                        indices.append((
                            isinstance(constraint, UniqueConstraint),
                            self._mysql_constraint_createstring(constraint)
                        ))

                        getattr(self.table, type).remove(constraint)
            # In case the database's DEFAULT CHARSET isn't set to UTF8
            self.table.kwargs['mysql_charset'] = 'utf8'

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

        sg = session.bind.dialect.schemagenerator(session.bind.dialect,
                session.bind)
        description = sg.get_column_specification(col)

        for constraint in constraints:
            sg.traverse_single(constraint)

        constraints = []
        foreign_key_re = re.compile(r'^FOREIGN KEY\(.*?\) (REFERENCES .*)$',
                                    re.I)
        for constraint in [x.strip() for x in sg.buffer.getvalue().split(',')]:
            m = foreign_key_re.match(constraint)
            if m:
                constraints.append(m.group(1))
            else:
                constraints.append(constraint)

        session.execute('ALTER TABLE "%s" ADD COLUMN %s %s;'
                % (table.name, description, " ".join(constraints)))

    def add_index(self, col):
        "Add an index to the table"

        engine = self.upgrade_session.bind.engine.name
        query = None

        if engine == 'mysql' and isinstance(col.type, IbidUnicodeText):
            query = 'ALTER TABLE "%s" ADD %s INDEX "%s" ("%s"(%i));' % (
                    self.table.name, col.unique and 'UNIQUE' or '',
                    self._index_name(col), col.name, col.type.index_length)
        elif engine == pg_engine:
            # SQLAlchemy hangs if it tries to do this, because it forgets the ;
            query = 'CREATE %s INDEX "%s" ON "%s" ("%s")' % (
                    col.unique and 'UNIQUE' or '',self._index_name(col),
                    self.table.name, col.name)

        try:
            if query is not None:
                self.upgrade_session.execute(query)
            else:
                Index(self._index_name(col), col, unique=col.unique) \
                        .create(bind=self.upgrade_session.bind)

        # We understand that occasionaly we'll duplicate an Index.
        # This is due to differences in index-creation requirements
        # between DBMS
        except OperationalError, e:
            if engine == 'sqlite' and u'already exists' in unicode(e):
                return
            if engine == 'mysql' and u'Duplicate' in unicode(e):
                return
            raise
        except ProgrammingError, e:
            if engine == pg_engine and u'already exists' in unicode(e):
                return
            raise

    def drop_index(self, col):
        "Drop an index from the table"

        engine = self.upgrade_session.bind.engine.name

        try:
            if isinstance(col, Column):
                Index(self._index_name(col), col, unique=col.unique) \
                        .drop(bind=self.upgrade_session.bind)
            else:
                col.drop()

        except OperationalError, e:
            if engine == 'sqlite' and u'no such index' in unicode(e):
                return
            if engine == 'mysql' \
                    and u'check that column/key exists' in unicode(e):
                return
            raise

        except ProgrammingError, e:
            if engine == pg_engine and u'does not exist' in unicode(e):
                return

        # Postgres constraints can be attached to tables and can't be dropped
        # at DB level.
        except InternalError, e:
            if engine == pg_engine:
                self.upgrade_session.execute(
                        'ALTER TABLE "%s" DROP CONSTRAINT "%s"' % (
                        self.table.name, self._index_name(col)))

    def drop_column(self, col_name):
        "Drop column col_name from table"

        session = self.upgrade_session

        log.debug(u"Dropping column %s from table %s",
                col_name, self.table.name)

        if session.bind.engine.name == 'sqlite':
            self._rebuild_sqlite({col_name: None})
        else:
            session.execute('ALTER TABLE "%s" DROP COLUMN "%s";'
                    % (self.table.name, col_name))

    def rename_column(self, col, old_name):
        "Rename column from old_name to Column col"

        session = self.upgrade_session
        table = self._get_reflected_model()

        log.debug(u"Rename column %s to %s in table %s",
                old_name, col.name, table.name)

        if session.bind.engine.name == 'sqlite':
            self._rebuild_sqlite({old_name: col})
        elif session.bind.engine.name == 'mysql':
            self.alter_column(col, old_name)
        else:
            session.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s";'
                    % (table.name, old_name, col.name))

    def alter_column(self, col, old_name=None, force_rebuild=False):
        """Change a column (possibly renaming from old_name) to Column col."""

        session = self.upgrade_session
        table = self._get_reflected_model()

        log.debug(u"Altering column %s in table %s", col.name, table.name)

        sg = session.bind.dialect.schemagenerator(session.bind.dialect,
                session.bind)
        description = sg.get_column_specification(col)
        old_col = table.c[old_name or col.name]

        # SQLite doesn't enforce value length restrictions
        # only type changes have a real effect
        if session.bind.engine.name == 'sqlite':
            if not force_rebuild and (
                (isinstance(col.type, (IbidUnicodeText, IbidUnicode))
                    and isinstance(old_col.type, (IbidUnicodeText, IbidUnicode)
                ) or (isinstance(col.type, Integer)
                    and isinstance(old_col.type, Integer)))):
                return

            self._rebuild_sqlite(
                    {old_name is None and col.name or old_name: col})

        elif session.bind.engine.name == 'mysql':
            # Special handling for columns of TEXT type, because SQLAlchemy
            # can't create indexes for them
            recreate = []
            if isinstance(col.type, IbidUnicodeText) \
                    or isinstance(old_col.type, IbidUnicodeText):
                for type in (table.constraints, table.indexes):
                    for constraint in list(type):
                        if any(True for column in constraint.columns
                                if old_col.name == column.name):

                            self.drop_index(constraint)

                            constraint.columns = [
                                (old_col.name == column.name) and col or column
                                for column in constraint.columns
                            ]
                            recreate.append((
                                isinstance(constraint, UniqueConstraint),
                                self._mysql_constraint_createstring(constraint)
                            ))

            session.execute('ALTER TABLE "%s" CHANGE "%s" %s;' %
                (table.name, old_col.name, description))

            for unique, columnspec in recreate:
                session.execute('ALTER TABLE "%s" ADD %s INDEX (%s);' %
                    (self.table.name, unique and 'UNIQUE' or '', columnspec))

        else:
            if old_name is not None:
                self.rename_column(col, old_name)

            session.execute('ALTER TABLE "%s" ALTER COLUMN "%s" TYPE %s;' %
                (table.name, col.name, description.split(" ", 3)[1]))

            if old_col.nullable != col.nullable:
                session.execute(
                    'ALTER TABLE "%s" ALTER COLUMN "%s" %s NOT NULL;'
                    % (table.name, col.name, col.nullable and 'DROP' or 'SET')
                )

    def _rebuild_sqlite(self, colmap):
        """
        SQLite doesn't support modification of table schema - must rebuild the
        table.
        colmap maps old column names to new Columns
        (or None for column deletion).
        Only modified columns need to be listed, unchaged columns are carried
        over automatically.
        Specify table in case name has changed in a more recent version.
        """

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

        session.execute('ALTER TABLE "%s" RENAME TO "%s_old";'
                % (table.name, table.name))

        # SQLAlchemy indexes aren't attached to tables, they must be dropped
        # around now or we'll get a clash
        for constraint in table.indexes:
            try:
                constraint.drop()
            except OperationalError:
                pass

        table.create()

        session.execute('INSERT INTO "%s" ("%s") SELECT "%s" FROM "%s_old";'
            % (
                table.name,
                '", "'.join(fullcolmap.values()),
                '", "'.join(fullcolmap.keys()),
                table.name
        ))

        session.execute('DROP TABLE "%s_old";' % table.name)

        # SQLAlchemy doesn't pick up all the indexes in the reflected table.
        # It's ok to use indexes that may be further in the future than this
        # upgrade because either we can already support them or we'll be
        # rebuilding again soon
        for constraint in self.table.indexes:
            try:
                constraint.create(bind=session.bind)
            except OperationalError:
                pass


class SchemaVersionException(Exception):
    """There is an out-of-date table.
    The message should be a list of out of date tables.
    """
    pass


def schema_version_check(sessionmaker):
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

    raise SchemaVersionException(u", ".join(upgrades))

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
