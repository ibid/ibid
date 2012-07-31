# Copyright (c) 2009-2011, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from sqlalchemy.types import Integer, DateTime, Boolean, \
                             Unicode as _Unicode, UnicodeText as _UnicodeText


def monkey_patch():
    import sqlalchemy.dialects.postgresql
    sqlalchemy.dialects.postgresql.dialect.ischema_names['citext'] = IbidUnicodeText
    def postgres_visit_IBID_VARCHAR(self, type_):
        if type_.case_insensitive:
            return 'CITEXT'
        else:
            return self.visit_VARCHAR(type_)
    sqlalchemy.dialects.postgresql.dialect.type_compiler.visit_IBID_VARCHAR = postgres_visit_IBID_VARCHAR
    def postgres_visit_IBID_TEXT(self, type_):
        if type_.case_insensitive:
            return 'CITEXT'
        else:
            return self.visit_TEXT(type_)
    sqlalchemy.dialects.postgresql.dialect.type_compiler.visit_IBID_TEXT = postgres_visit_IBID_TEXT

    import sqlalchemy.dialects.sqlite
    def sqlite_visit_IBID_VARCHAR(self, type_):
        if type_.case_insensitive:
            collation = 'NOCASE'
        else:
            collation = 'BINARY'
        return self.visit_VARCHAR(type_) + ' COLLATE ' + collation
    sqlalchemy.dialects.sqlite.dialect.type_compiler.visit_IBID_VARCHAR = sqlite_visit_IBID_VARCHAR
    def sqlite_visit_IBID_TEXT(self, type_):
        if type_.case_insensitive:
            collation = 'NOCASE'
        else:
            collation = 'BINARY'
        return self.visit_TEXT(type_) + ' COLLATE ' + collation
    sqlalchemy.dialects.sqlite.dialect.type_compiler.visit_IBID_TEXT = sqlite_visit_IBID_TEXT

    import sqlalchemy.dialects.mysql
    def mysql_visit_IBID_VARCHAR(self, type_):
        if type_.case_insensitive:
            collation = 'utf8_general_ci'
        else:
            collation = 'utf8_bin'
        return self.visit_VARCHAR(type_) + ' COLLATE ' + collation
    sqlalchemy.dialects.mysql.dialect.type_compiler.visit_IBID_VARCHAR = sqlite_visit_IBID_VARCHAR
    def mysql_visit_IBID_TEXT(self, type_):
        if type_.case_insensitive:
            collation = 'utf8_general_ci'
        else:
            collation = 'utf8_bin'
        return self.visit_TEXT(type_) + ' COLLATE ' + collation
    sqlalchemy.dialects.mysql.dialect.type_compiler.visit_IBID_TEXT = sqlite_visit_IBID_TEXT

class IbidUnicode(_Unicode):
    "Collaiton aware Unicode"

    __visit_name__ = 'IBID_VARCHAR'

    def __init__(self, length, case_insensitive=False, **kwargs):
        self.case_insensitive = case_insensitive
        super(IbidUnicode, self).__init__(length, **kwargs)

class IbidUnicodeText(_UnicodeText):
    "Collation aware UnicodeText"

    __visit_name__ = 'IBID_TEXT'

    def __init__(self, index_length=8, case_insensitive=False, **kwargs):
        self.case_insensitive = case_insensitive
        self.index_length = index_length
        super(IbidUnicodeText, self).__init__(**kwargs)

monkey_patch()

# vi: set et sta sw=4 ts=4:
