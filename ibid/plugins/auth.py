from sqlalchemy.orm.exc import NoResultFound

import ibid
from ibid.plugins import Processor, match
from ibid.auth_ import Credential, Permission
from ibid.plugins.identity import Account

class AddAuth(Processor):

    @match('^\s*authenticate\s+(.+?)(?:\s+on\s+(.+))?\s+using\s+(\S+)\s+(.+)\s*$')
    def handler(self, event, user, source, method, credential):

        session = ibid.databases.ibid()
        try:
            account = session.query(Account).filter_by(username=user).one()
        except NoResultFound:
            event.addresponse(u"I don't know who %s is" % user)
            session.close()
            return

        credential = Credential(method, credential, source, account.id)
        session.add(credential)
        session.commit()
        session.close()

        event.addresponse(u'Okay')

class Permissions(Processor):

    @match('^grant\s+(.+)\s+permission\s+(.+)$')
    def grant(self, event, user, permission):

        session = ibid.databases.ibid()
        try:
            account = session.query(Account).filter_by(username=user).one()
        except NoResultFound:
            event.addresponse(u"I don't know who %s is" % user)
            session.close()
            return

        permission = Permission(permission, account.id)
        session.add(permission)
        session.commit()
        session.close()

        event.addresponse(u'Okay')

    @match(r'^permissions(?:\s+for\s+(\S+))?$')
    def list(self, event, username):
        session = ibid.databases.ibid()
        if not username:
            if not event.account:
                event.addresponse(u"I don't know who you are")
                return
            account = session.query(Account).filter_by(id=event.account).one()
        else:
            try:
                account = session.query(Account).filter_by(username=username).one()
            except NoResultFound:
                event.addresponse(u"I don't know who %s is" % username)
                return

        event.addresponse(', '.join([perm.permission for perm in account.permissions]))

class Auth(Processor):

    @match('^\s*auth(?:\s+(.+))?\s*$')
    def handler(self, event, password):
        result = ibid.auth.authenticate(event, password)
        if result:
            event.addresponse(u'You are authenticated')
        else:
            event.addresponse(u'Authentication failed')

# vi: set et sta sw=4 ts=4:
