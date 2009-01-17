from traceback import print_exc
from time import time
import logging

from twisted.internet import reactor
from sqlalchemy import or_

import ibid
from ibid.models import Credential, Permission, Account
from ibid.plugins.auth import hash, permission

class Auth(object):

    log = logging.getLogger('core.auth')

    def __init__(self):
        self.cache = {}

    def authenticate(self, event, credential=None):

        if 'account' not in event or not event.account:
            self.log.debug(u"Authentication for %s (%s) failed because identity doesn't have an account", event.identity, event.sender)
            return False

        config = ibid.config.auth
        methods = []
        if 'auth' in ibid.config.sources[event.source]:
            methods.extend(ibid.config.sources[event.source]['auth'])
        methods.extend(config['methods'])

        if event.sender in self.cache:
            timestamp = self.cache[event.sender]
            if time() - timestamp < ibid.config.auth['timeout']:
                self.log.debug(u"Authenticated %s/%s (%s) from cache", event.account, event.identity, event.sender)
                return True
            else:
                del self.cache[event.sender]

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
                    self.log.info(u"Authenticated %s/%s (%s) using %s", event.account, event.identity, event.sender, method)
                    self.cache[event.sender] = time()
                    return True
            except:
                print_exc()

        self.log.info(u"Authentication for %s/%s (%s) failed", event.account, event.identity, event.sender)
        return False

    def authorise(self, event, name):
        value = permission(name, event.account, event.source)
        self.log.info(u"Checking %s permission for %s/%s (%s): %s", name, event.account, event.identity, event.sender, value)

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
