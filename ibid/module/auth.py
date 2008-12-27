import ibid
from ibid.module import Module
from ibid.decorators import addressed, notprocessed, match
from ibid.auth_ import Authenticator, Permission
from ibid.module.identity import identify

class AddAuth(Module):

    @addressed
    @notprocessed
    @match('^\s*authenticate\s+(.+?)(?:\s+on\s+(.+))?\s+using\s+(\S+)\s+(.+)\s*$')
    def process(self, event, user, source, method, authenticator):

        account = identify(user, event.source)
        if not account:
            event.addresponse(u"I don't know who %s is" % user)

        else:
            authenticator = Authenticator(account.id, source, method, authenticator)
            session = ibid.databases.ibid()
            session.add(authenticator)
            session.commit()

            event.addresponse(u'Okay')

class AddPermission(Module):

    @addressed
    @notprocessed
    @match('^\s*grant\s+(.+)\s+permission\s+(.+)\s*$')
    def process(self, event, user, permission):

        account = identify(user, event.source)
        if not account:
            event.addresponse(u"I don't know who %s is" % user)

        else:
            permission = Permission(account.id, permission)
            session = ibid.databases.ibid()
            session.add(permission)
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
