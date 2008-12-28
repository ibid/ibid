from traceback import print_exc
from time import time

from twisted.internet import reactor
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound

import ibid
from ibid.models import Credential, Permission, Account

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
                event.authenticated = True
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
                    event.authenticated = True
                    return True
            except:
                print_exc()

        return False

    def authorise(self, event, permission):

        if 'authenticated' not in event:
            return False

        session = ibid.databases.ibid()
        return session.query(Permission).filter_by(account_id=event.account).filter_by(permission=permission).first() and True or False

    def implicit(self, event, credential = None):
        return True

    def password(self, event, password):
        if password is None:
            return False

        session = ibid.databases.ibid()
        for credential in session.query(Credential).filter_by(method='password').filter_by(account_id=event.account).filter(or_(Credential.source == event.source, Credential.source == None)).all():
            if credential.credential == password:
                return True

# vi: set et sta sw=4 ts=4:
