#!/usr/bin/env python

import sys
from sys import exit, stdin
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from getpass import getpass

import ibid.plugins
from ibid.plugins.auth import hash
from ibid.config import FileConfig
from ibid.models import Account, Identity, Permission, Credential

config = FileConfig('ibid.ini')

bases = [('ibid.models', 'Base'), ('ibid.plugins.factoid', 'Base')]
metadatas = []
engine = create_engine(config.databases['ibid']['uri'])

for module, model in bases:
    __import__(module)
    klass = eval('%s.%s' % (module, model))
    klass.metadata.create_all(engine)

for module, metadata in metadatas:
    __import__(module)
    klass = eval('%s.%s' % (module, metadata))
    klass.create_all(engine)

print u'Database tables created'

print 'Enter your nick/JID: ',
identity = unicode(stdin.readline().strip())
print 'Enter the source name: ',
source = unicode(stdin.readline().strip())
pass1 = getpass('Enter your password: ')
pass2 = getpass('Confirm password: ')

if pass1 != pass2:
    print 'Password do not match'
    exit(1)

Session = sessionmaker(bind=engine)
session = Session()
account = Account(identity)
identity = Identity(source, identity)
account.identities.append(identity)

for permission in (u'accounts', u'sources', u'plugins', u'core', u'admin', u'config', u'saydo'):
    perm = Permission(permission, u'auth')
    account.permissions.append(perm)

credential = Credential(u'password', hash(unicode(pass1)))
account.credentials.append(credential)

session.add(account)
session.add(identity)
session.commit()
session.close()

print 'Account created with admin permissions'

# vi: set et sta sw=4 ts=4:
