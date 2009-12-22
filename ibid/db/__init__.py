from ibid.db.types import TypeDecorator, Integer, DateTime, Boolean, \
                          IbidUnicode, IbidUnicodeText

from sqlalchemy import Table, Column, ForeignKey, Index, UniqueConstraint, \
                       PassiveDefault, or_, MetaData as _MetaData
from sqlalchemy.orm import eagerload, relation, synonym
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base as _declarative_base

from sqlalchemy.exceptions import IntegrityError

metadata = _MetaData()
Base = _declarative_base(metadata=metadata)

from ibid.db.versioned_schema import VersionedSchema, SchemaVersionException, \
                                     schema_version_check, upgrade_schemas

# vi: set et sta sw=4 ts=4:
