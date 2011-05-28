# Copyright (c) 2009-2010, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from sqlalchemy import __version__ as _sqlalchemy_version
from sqlalchemy.types import Integer, DateTime, Boolean, \
                             Unicode as _Unicode, UnicodeText as _UnicodeText

if _sqlalchemy_version < '0.6':
    from sqlalchemy.types import TypeDecorator
    custom_type_class = TypeDecorator
    pg_engine = 'postgres'
else:
    from sqlalchemy.types import UserDefinedType
    custom_type_class = UserDefinedType
    pg_engine = 'postgresql'

class _CIDecorator(custom_type_class):
    "Abstract class for collation aware columns"

    def __init__(self, length=None, case_insensitive=False):
        self.case_insensitive = case_insensitive
        super(_CIDecorator, self).__init__(length=length)

    def load_dialect_impl(self, dialect):
        # SA 0.5 only:
        # Figure out what we are connected to
        self.dialect = dialect.name

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
            elif self.dialect == pg_engine and self.case_insensitive:
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
