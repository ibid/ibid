# Copyright (c) 2008-2009, Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from time import time
from random import choice
import string
import logging
import re

from sqlalchemy import or_

import ibid
from ibid.compat import hashlib
from ibid.db.models import Credential, Permission

def hash(password, salt=None):
    if salt:
        salt = salt[:8]
    else:
        chars = string.letters + string.digits
        salt = ''.join([choice(chars) for i in xrange(8)])
    return unicode(salt + hashlib.sha1(salt + password).hexdigest())

def permission(name, account, source, session):
    if account:
        permission = session.query(Permission) \
                .filter_by(account_id=account, name=name) \
                .first()

        if permission:
            return permission.value

    permissions = []
    permissions.extend(ibid.sources[source].permissions)
    if 'permissions' in ibid.config.auth:
        permissions.extend(ibid.config.auth['permissions'])

    for permission in permissions:
        permission_re = re.compile('^([+-]?)(\S+)$')
        match = permission_re.match(permission)
        if match and match.group(2) == name :
            if match.group(1) == '+':
                return 'yes'
            elif match.group(1) == '-':
                return 'no'
            else:
                return 'auth'

    return 'no'

class Auth(object):

    def __init__(self):
        self.authentication_cache = {}
        self.authorisation_cache = {}
        self.log = logging.getLogger('core.auth')

    def drop_caches(self):
        "Authentication / Authorisation data changed"
        self.authentication_cache = {}
        self.authorisation_cache = {}

    def authenticate(self, event, credential=None):
        if 'account' not in event or not event.account:
            self.log.debug(u"Authentication for %s (%s) failed because identity doesn't have an account", event.identity, event.sender['connection'])
            return False

        config = ibid.config.auth
        methods = []
        methods.extend(ibid.sources[event.source].auth)
        methods.extend(config['methods'])

        if event.sender['connection'] in self.authentication_cache:
            timestamp = self.authentication_cache[event.sender['connection']]
            if time() - timestamp < ibid.config.auth['timeout']:
                self.log.debug(u"Authenticated %s/%s (%s) from cache", event.account, event.identity, event.sender['connection'])
                return True
            else:
                del self.authentication_cache[event.sender['connection']]

        for method in methods:
            if hasattr(ibid.sources[event.source], 'auth_%s' % method):
                function = getattr(ibid.sources[event.source], 'auth_%s' % method)
            elif hasattr(self, method):
                function = getattr(self, method)
            else:
                self.log.warning(u"Couldn't find authentication method %s", method)
                continue

            try:
                if function(event, credential):
                    self.log.info(u"Authenticated %s/%s (%s) using %s", event.account, event.identity, event.sender['connection'], method)
                    self.authentication_cache[event.sender['connection']] = time()
                    return True
            except:
                self.log.exception(u"Exception occured in %s auth method", method)

        self.log.info(u"Authentication for %s/%s (%s) failed", event.account, event.identity, event.sender['connection'])
        return False

    def authorise(self, event, name):
        "Check if event comes from a user with permission 'name'"
        key = (name, event.account, event.source)
        if key not in self.authorisation_cache:
            value = permission(session=event.session, *key)
            self.authorisation_cache[key] = value
            self.log.info(u"Checking %s permission for %s/%s (%s): %s",
                    name, event.account, event.identity,
                    event.sender['connection'], value)
        else:
            value = self.authorisation_cache[key]
            self.log.debug(u"Checking %s permission for %s/%s (%s) from cache: %s",
                    name, event.account, event.identity,
                    event.sender['connection'], value)

        if value == 'auth':
            return self.authenticate(event)
        return value == 'yes'

    def implicit(self, event, credential=None):
        return True

    def password(self, event, password):
        if password is None:
            return False

        for credential in event.session.query(Credential) \
                .filter_by(method=u'password', account_id=event.account) \
                .filter(or_(Credential.source == event.source,
                            Credential.source == None)) \
                .all():
            if hash(password, credential.credential) == credential.credential:
                return True

# vi: set et sta sw=4 ts=4:
