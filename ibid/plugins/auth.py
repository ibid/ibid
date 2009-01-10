import string
from hashlib import sha512
from random import choice

from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match, auth_responses, authorise
from ibid.auth_ import Credential, Permission
from ibid.plugins.identity import Account

help = {}

chars = string.letters + string.digits

def hash(password):
    salt = ''.join([choice(chars) for i in xrange(8)])
    return unicode(salt + sha512(salt + password).hexdigest())

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
            password = hash(credential)
            event.message = event.message[:-len(credential)] + password
            event.message_raw = event.message_raw[:event.message_raw.rfind(credential)] + password + event.message_raw[event.message_raw.rfind(credential)+len(credential):]
            credential = password

        credential = Credential(method, credential, source, account.id)
        session.save_or_update(credential)
        session.commit()
        session.close()

        event.addresponse(u'Okay')

permission_values = {'no': '-', 'yes': '+', 'auth': ''}
class Permissions(Processor):
    """(grant|revoke|remove) <permission> (to|from|on) <username> [when authed] | list permissions"""
    feature = 'auth'

    @match(r'^(grant|revoke|remove)\s+(.+?)\s+(?:to|from|on)\s+(.+?)(\s+(?:with|when|if)\s+(?:auth|authed|authenticated))?$')
    @authorise('admin')
    def grant(self, event, action, name, username, auth):

        session = ibid.databases.ibid()
        account = session.query(Account).filter_by(username=username).first()
        if not account:
            event.addresponse(u"I don't know who %s is" % username)
            session.close()
            return

        permission = session.query(Permission).filter_by(account_id=account.id).filter(func.lower(Permission.name)==name.lower()).first()
        if action.lower() == 'remove':
            if permission:
                session.delete(permission)
            else:
                event.addresponse(u"%s doesn't have that permission anyway")
                return

        else:
            if not permission:
                permission = Permission(name, account_id=account.id)

            if action.lower() == 'revoke':
                value = 'no'
            elif auth:
                value = 'auth'
            else:
                value = 'yes'

            permission.value = value
            session.save_or_update(permission)

        session.commit()
        session.close()

        event.addresponse(True)

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

        event.addresponse(', '.join(['%s%s' % (permission_values[perm.value], perm.name) for perm in account.permissions]))

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
