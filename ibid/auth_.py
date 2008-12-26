from fnmatch import fnmatch
from time import time

from sqlalchemy import Column, Integer, String, DateTime, or_
from sqlalchemy.ext.declarative import declarative_base

import ibid

Base = declarative_base()
class Token(Base):
    __tablename__ = 'auth'

    id = Column(Integer, primary_key=True)
    user = Column(String)
    source = Column(String)
    method = Column(String)
    token = Column(String)

    def __init__(self, user, source, method, token):
        self.user = user
        self.source = source
        self.method = method
        self.token = token

class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True)
    user = Column(String)
    permission = Column(String)

    def __init__(self, user, permission):
        self.user = user
        self.permission = permission

class Auth(object):

    def __init__(self):
        self.cache = {}

    def authenticate(self, event, password=None):

        config = ibid.config.auth
        methods = []
        if 'auth' in ibid.config.sources[event.source]:
            methods.extend(ibid.config.sources[event.source]['auth'])
        methods.extend(config['methods'])

        if event.sender in self.cache:
            (user, timestamp) = self.cache[event.sender]
            if time() - timestamp < ibid.config.auth['timeout']:
                event.user = user
                return True
            else:
                del self.cache[event.sender]

        for method in methods:
            if hasattr(self, method):
                if getattr(self, method)(event, password):
                    self.cache[event.sender] = (event.user, time())
                    return True

        return False

    def authorise(self, event, permission):

        if 'user' not in event:
            return False

        session = ibid.databases.ibid()
        if session.query(Permission).filter_by(user=event.user).filter_by(permission=permission).first():
            return True

        return False

    def jid(self, event, password = None):
        if ibid.config.sources[event.source]['type'] == 'jabber':
            event.user = event.sender.split('/')[0]
            return True

    def hostmask(self, event, password = None):
        if ibid.config.sources[event.source]['type'] != 'irc':
            return

        session = ibid.databases.ibid()
        for token in session.query(Token).filter_by(method='hostmask').filter_by(user=event.who).filter(or_(Token.source == event.source, Token.source == None)).all():
            if fnmatch(event.sender, token.token):
                event.user = event.who
                return True

    def password(self, event, password):
        if password is None:
            return False

        session = ibid.databases.ibid()
        for token in session.query(Token).filter_by(method='password').filter_by(user=event.who).filter(or_(Token.source == event.source, Token.source == None)).all():
            if token.token == password:
                event.user = event.who
                return True
        
# vi: set et sta sw=4 ts=4:
