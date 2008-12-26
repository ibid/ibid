import ibid
from ibid.module import Module
from ibid.decorators import *
from ibid.auth_ import Token, Permission

class AddAuth(Module):

    @addressed
    @notprocessed
    @match('^\s*add\s+auth\s+for\s+(.+?)(?:\s+on\s+(.+))?\s+using\s+(\S+)\s+(.+)\s*$')
    def process(self, event, user, source, method, token):

        tok = Token(user, source, method, token)
        session = ibid.databases.ibid()
        session.add(tok)
        session.commit()

        event.addresponse(u'Okay')

class AddPermission(Module):

    @addressed
    @notprocessed
    @match('^\s*add\s+permission\s+(.+)\s+for\s+(.+)\s*$')
    def process(self, event, permission, user):

        perm = Permission(user, permission)
        session = ibid.databases.ibid()
        session.add(perm)
        session.commit()

        event.addresponse(u'Okay')

class Auth(Module):

    @addressed
    @notprocessed
    @match('^\s*auth(?:\s+(.+))?\s*$')
    def process(self, event, password):
        result = ibid.auth.authenticate(event, password)
        if result:
            event.addresponse(u'You are authenticated')
        else:
            event.addresponse(u'Authentication failed')

# vi: set et sta sw=4 ts=4:
