#!/usr/bin/env python

import sys
from sqlalchemy import create_engine

import ibid.module

models = [('ibid.module.seen', 'Base'), ('ibid.auth_', 'Base')]
engine = create_engine('sqlite:///ibid.db')

for module, model in models:
    __import__(module)
    klass = eval('%s.%s' % (module, model))
    klass.metadata.create_all(engine)

# vi: set et sta sw=4 ts=4:
