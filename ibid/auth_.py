from traceback import print_exc
from time import time
import re

from twisted.internet import reactor
from sqlalchemy import or_

import ibid
from ibid.models import Credential, Permission, Account
from ibid.plugins.auth import hash

permission_re = re.compile('^([+-]?)(\S+)$')

class Auth(object):

    def __init__(self):
        self.cache = {}

    def authenticate(self, event, credential=None):

        if 'account' not in event:
            return

        config = ibid.config.auth
        methods = []
        if 'auth' in ibid.config.sources[event.source]:
            methods.extend(ibid.config.sources[event.source]['auth'])
        methods.extend(config['methods'])

        if event.sender in self.cache:
            timestamp = self.cache[event.sender]
            if time() - timestamp < ibid.config.auth['timeout']:
                return True
            else:
                del self.cache[event.sender]

        for method in methods:
            if hasattr(ibid.sources[event.source.lower()], 'auth_%s' % method):
                function = getattr(ibid.sources[event.source.lower()], 'auth_%s' % method)
            elif hasattr(self, method):
                function = getattr(self, method)
            else:
                print "Couldn't find auth method %s" % method
                continue

            try:
                if function(event, credential):
                    self.cache[event.sender] = time()
                    return True
            except:
                print_exc()

        return False

    def authorise(self, event, name):

        if event.account:
            session = ibid.databases.ibid()
            permission = session.query(Permission).filter_by(account_id=event.account).filter_by(name=name).first()
            session.close()

            if permission:
                if permission.value == 'no':
                    return False
                elif permission.value == 'yes':
                    return True
                elif permission.value == 'auth':
                    return self.authenticate(event)

        permissions = []
        if 'permissions' in ibid.config.sources[event.source]:
            permissions.extend(ibid.config.sources[event.source]['permissions'])
        if 'permissions' in ibid.config.auth:
            permissions.extend(ibid.config.auth['permissions'])

        for permission in permissions:
            match = permission_re.match(permission)
            if match and match.group(2) == name :
                if match.group(1) == '+':
                    return True
                elif match.group(1) == '-':
                    return False
                else:
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
