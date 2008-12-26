from fnmatch import fnmatch

from sqlalchemy import Column, Integer, String, DateTime
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

class Auth(object):

    def authenticate(self, event):

        config = ibid.config.auth
        methods = []
        if 'auth' in ibid.config.sources[event.source]:
            methods.extend(ibid.config.sources[event.source]['auth'])
        methods.extend(config['methods'])

        for method in methods:
            if hasattr(self, method):
                if getattr(self, method)(event):
                    return True

        return False

    def jid(self, event):
        if ibid.config.sources[event.source]['type'] == 'jabber':
            event.user = event.sender.split('/')[0]
            return True

    def hostmask(self, event):
        if ibid.config.sources[event.source]['type'] != 'irc':
            return

        session = ibid.databases.ibid()
        for token in session.query(Token).filter_by(user=event.who).all():
            if token.source and token.source != event.source:
                continue

            if fnmatch(event.sender, token.token):
                event.user = event.who
                return True
        
# vi: set et sta sw=4 ts=4:
