from time import time
from random import choice
import string
import logging
import re
try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1

from sqlalchemy import or_

import ibid
from ibid.models import Credential, Permission

chars = string.letters + string.digits
permission_re = re.compile('^([+-]?)(\S+)$')

def hash(password, salt=None):
    if salt:
        salt = salt[:8]
    else:
        salt = ''.join([choice(chars) for i in xrange(8)])
    return unicode(salt + sha1(salt + password).hexdigest())

def permission(name, account, source):
    if account:
        session = ibid.databases.ibid()
        permission = session.query(Permission).filter_by(account_id=account).filter_by(name=name).first()
        session.close()

        if permission:
            return permission.value

    permissions = []
    permissions.extend(ibid.sources[source.lower()].permissions)
    if 'permissions' in ibid.config.auth:
        permissions.extend(ibid.config.auth['permissions'])

    for permission in permissions:
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
        self.cache = {}
        self.log = logging.getLogger('core.auth')

    def authenticate(self, event, credential=None):

        if 'account' not in event or not event.account:
            self.log.debug(u"Authentication for %s (%s) failed because identity doesn't have an account", event.identity, event.sender['connection'])
            return False

        config = ibid.config.auth
        methods = []
        methods.extend(ibid.sources[event.source.lower()].auth)
        methods.extend(config['methods'])

        if event.sender['connection'] in self.cache:
            timestamp = self.cache[event.sender['connection']]
            if time() - timestamp < ibid.config.auth['timeout']:
                self.log.debug(u"Authenticated %s/%s (%s) from cache", event.account, event.identity, event.sender['connection'])
                return True
            else:
                del self.cache[event.sender['connection']]

        for method in methods:
            if hasattr(ibid.sources[event.source.lower()], 'auth_%s' % method):
                function = getattr(ibid.sources[event.source.lower()], 'auth_%s' % method)
            elif hasattr(self, method):
                function = getattr(self, method)
            else:
                self.log.warning(u"Couldn't find authentication method %s", method)
                continue

            try:
                if function(event, credential):
                    self.log.info(u"Authenticated %s/%s (%s) using %s", event.account, event.identity, event.sender['connection'], method)
                    self.cache[event.sender['connection']] = time()
                    return True
            except:
                self.log.exception(u"Exception occured in %s auth method", method)

        self.log.info(u"Authentication for %s/%s (%s) failed", event.account, event.identity, event.sender['connection'])
        return False

    def authorise(self, event, name):
        value = permission(name, event.account, event.source)
        self.log.info(u"Checking %s permission for %s/%s (%s): %s", name, event.account, event.identity, event.sender['connection'], value)

        if value == 'yes':
            return True
        elif value == 'auth':
            return self.authenticate(event)

        return False

    def implicit(self, event, credential = None):
        return True

    def password(self, event, password):
        if password is None:
            return False

        session = ibid.databases.ibid()
        for credential in session.query(Credential).filter_by(method=u'password').filter_by(account_id=event.account).filter(or_(Credential.source == event.source, Credential.source == None)).all():
            if hash(password, credential.credential) == credential.credential:
                return True

# vi: set et sta sw=4 ts=4:
