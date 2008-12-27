#!/usr/bin/env python

import sys
from sqlalchemy import create_engine

import ibid.plugins

models = [('ibid.models', 'Base')]
engine = create_engine('sqlite:///ibid.db')

for module, model in models:
    __import__(module)
    klass = eval('%s.%s' % (module, model))
    klass.metadata.create_all(engine)

# vi: set et sta sw=4 ts=4:
