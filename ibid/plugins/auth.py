import ibid
from ibid.plugins import Processor, match
from ibid.auth_ import Authenticator, Permission
from ibid.plugins.identity import identify

class AddAuth(Processor):

    @match('^\s*authenticate\s+(.+?)(?:\s+on\s+(.+))?\s+using\s+(\S+)\s+(.+)\s*$')
    def handler(self, event, user, source, method, authenticator):

        account = identify(event.source, user)
        if not account:
            event.addresponse(u"I don't know who %s is" % user)

        else:
            authenticator = Authenticator(account.id, source, method, authenticator)
            session = ibid.databases.ibid()
            session.add(authenticator)
            session.commit()

            event.addresponse(u'Okay')

class AddPermission(Processor):

    @match('^\s*grant\s+(.+)\s+permission\s+(.+)\s*$')
    def handler(self, event, user, permission):

        account = identify(event.source, user)
        if not account:
            event.addresponse(u"I don't know who %s is" % user)

        else:
            permission = Permission(account.id, permission)
            session = ibid.databases.ibid()
            session.add(permission)
            session.commit()

            event.addresponse(u'Okay')

class Auth(Processor):

    @match('^\s*auth(?:\s+(.+))?\s*$')
    def handler(self, event, password):
        result = ibid.auth.authenticate(event, password)
        if result:
            event.addresponse(u'You are authenticated')
        else:
            event.addresponse(u'Authentication failed')

# vi: set et sta sw=4 ts=4:
