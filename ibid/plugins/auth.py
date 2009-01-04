import string
from hashlib import sha512
from random import choice

import ibid
from ibid.plugins import Processor, match, auth_responses, authorise
from ibid.auth_ import Credential, Permission
from ibid.plugins.identity import Account

help = {}

chars = string.letters + string.digits

def hash(password):
    salt = ''.join([choice(chars) for i in xrange(8)])
    return salt + sha512(salt + password).hexdigest()

help['auth'] = 'Adds and removes authentication credentials and permissions'
class AddAuth(Processor):
    """authenticate <account> using <method> [<credential>]"""
    feature = 'auth'

    @match(r'^authenticate\s+(.+?)(?:\s+on\s+(.+))?\s+using\s+(\S+)\s+(.+)$')
    def handler(self, event, user, source, method, credential):

        session = ibid.databases.ibid()
        if user.lower() == 'me':
            if not event.account:
                event.addresponse(u"I don't know who you are")
                return
            account = session.query(Account).filter_by(id=event.account).first()

        else:
            if not auth_responses(event, 'admin'):
                return
            account = session.query(Account).filter_by(username=user).first()
            if not account:
                event.addresponse(u"I don't know who %s is" % user)
                session.close()
                return

        if source:
            source = ibid.sources[source.lower()].name

        if method.lower() == 'password':
            credential = hash(credential)

        credential = Credential(method, credential, source, account.id)
        session.add(credential)
        session.commit()
        session.close()

        event.addresponse(u'Okay')

class Permissions(Processor):
    """grant <account> permission <permission> | list permissions"""
    feature = 'auth'

    @match(r'^grant\s+(.+)\s+permission\s+(.+)$')
    @authorise('admin')
    def grant(self, event, user, permission):

        session = ibid.databases.ibid()
        account = session.query(Account).filter_by(username=user).first()
        if not account:
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
            account = session.query(Account).filter_by(id=event.account).first()
        else:
            account = session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is" % username)
                return

        event.addresponse(', '.join([perm.permission for perm in account.permissions]))

class Auth(Processor):
    """auth <credential>"""
    feature = 'auth'

    @match(r'^auth(?:\s+(.+))?$')
    def handler(self, event, password):
        result = ibid.auth.authenticate(event, password)
        if result:
            event.addresponse(u'You are authenticated')
        else:
            event.addresponse(u'Authentication failed')

# vi: set et sta sw=4 ts=4:
