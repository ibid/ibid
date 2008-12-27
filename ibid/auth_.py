from fnmatch import fnmatch
from time import time, sleep
from traceback import print_exc

from twisted.internet import reactor
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound

import ibid
from ibid.models import Authenticator, Permission, Account

class Auth(object):

    def __init__(self):
        self.cache = {}
        self.irc = {}

    def authenticate(self, event, password=None):

        if 'user' not in event:
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
            if hasattr(self, method):
                try:
                    if getattr(self, method)(event, password):
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
        account = session.query(Account).filter_by(username=event.user).one()
        try:
            if session.query(Permission).filter_by(account_id=account.id).filter_by(permission=permission).one():
                return True
        except NoResultFound:
            return False
        finally:
            session.close()

    def implicit(self, event, password = None):
        return True

    def hostmask(self, event, password = None):
        if ibid.config.sources[event.source]['type'] != 'irc':
            return

        session = ibid.databases.ibid()
        account = session.query(Account).filter_by(username=event.user).one()
        for authenticator in session.query(Authenticator).filter_by(method='hostmask').filter_by(account_id=account.id).filter(or_(Authenticator.source == event.source, Authenticator.source == None)).all():
            if fnmatch(event.sender, authenticator.authenticator):
                return True

    def password(self, event, password):
        if password is None:
            return False

        session = ibid.databases.ibid()
        account = session.query(Account).filter_by(username=event.user).one()
        for authenticator in session.query(Authenticator).filter_by(method='password').filter_by(account_id=account.id).filter(or_(Authenticator.source == event.source, Authenticator.source == None)).all():
            if authenticator.authenticator == password:
                return True

    def _irc_auth_callback(self, nick, result):
        self.irc[nick] = result

    def nickserv(self, event, password):
        if ibid.config.sources[event.source]['type'] != 'irc':
            return

        reactor.callFromThread(ibid.sources[event.source].proto.authenticate, event.who, self._irc_auth_callback)
        for i in xrange(150):
            if event.who in self.irc:
                break
            sleep(0.1)

        if event.who in self.irc:
            result = self.irc[event.who]
            del self.irc[event.who]
            return result
        
# vi: set et sta sw=4 ts=4:
