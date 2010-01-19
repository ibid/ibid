# Copyright (c) 2009-2010, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from sqlalchemy.types import TypeDecorator, Integer, DateTime, Boolean, \
                             Unicode as _Unicode, UnicodeText as _UnicodeText

class _CIDecorator(TypeDecorator):
    "Abstract class for collation aware columns"

    def __init__(self, length=None, case_insensitive=False):
        self.case_insensitive = case_insensitive
        super(_CIDecorator, self).__init__(length=length)

    def load_dialect_impl(self, dialect):
        if hasattr(dialect, 'name'):
            self.dialect = dialect.name
        # SQLAlchemy 0.4:
        else:
            self.dialect = {
                'SQLiteDialect': 'sqlite',
                'PGDialect': 'postgres',
                'MySQLDialect': 'mysql',
            }[dialect.__class__.__name__]

        return dialect.type_descriptor(self.impl)

    def get_col_spec(self):
        colspec = self.impl.get_col_spec()
        if hasattr(self, 'case_insensitive'):
            collation = None
            if self.dialect == 'mysql':
                if self.case_insensitive:
                    collation = 'utf8_general_ci'
                else:
                    collation = 'utf8_bin'
            elif self.dialect == 'sqlite':
                if self.case_insensitive:
                    collation = 'NOCASE'
                else:
                    collation = 'BINARY'
            elif self.dialect == 'postgres' and self.case_insensitive:
                return 'CITEXT'

            if collation is not None:
                return colspec + ' COLLATE ' + collation
        return colspec

class IbidUnicode(_CIDecorator):
    "Collaiton aware Unicode"

    impl = _Unicode

    def __init__(self, length, **kwargs):
        super(IbidUnicode, self).__init__(length, **kwargs)

class IbidUnicodeText(_CIDecorator):
    "Collation aware UnicodeText"

    impl = _UnicodeText

    def __init__(self, index_length=8, **kwargs):
        self.index_length = index_length
        super(IbidUnicodeText, self).__init__(length=None, **kwargs)

# vi: set et sta sw=4 ts=4:
