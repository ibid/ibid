import string
from random import choice
import re
import logging
try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1

from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match, auth_responses, authorise
from ibid.models import Credential, Permission
from ibid.plugins.identity import Account

help = {}

log = logging.getLogger('plugins.auth')

chars = string.letters + string.digits
permission_re = re.compile('^([+-]?)(\S+)$')
actions = {'revoke': 'Revoked', 'grant': 'Granted', 'remove': 'Removed'}

def hash(password, salt=None):
    if salt:
        salt = salt[:8]
    else:
        salt = ''.join([choice(chars) for i in xrange(8)])
    return unicode(salt + sha1(salt + password).hexdigest())

def permission(name, account, source):
    if account:
        session = ibid.databases.ibid()
        permission = session.query(Permission).filter_by(account_id=account).filter_by(name=name).first()
        session.close()

        if permission:
            return permission.value

    permissions = []
    if 'permissions' in ibid.config.sources[source]:
        permissions.extend(ibid.config.sources[source]['permissions'])
    if 'permissions' in ibid.config.auth:
        permissions.extend(ibid.config.auth['permissions'])

    for permission in permissions:
        match = permission_re.match(permission)
        if match and match.group(2) == name :
            if match.group(1) == '+':
                return 'yes'
            elif match.group(1) == '-':
                return 'no'
            else:
                return 'auth'

    return 'no'

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
        session.flush()
        log.info(u"Added %s credential %s for account %s (%s) on %s by account %s", method, credential.credential, account.id, account.username, source, event.account)
        session.close()

        event.addresponse(u'Okay')

permission_values = {'no': '-', 'yes': '+', 'auth': ''}
class Permissions(Processor):
    """(grant|revoke|remove) <permission> (to|from|on) <username> [when authed] | list permissions"""
    feature = 'auth'

    permission = u'admin'

    @match(r'^(grant|revoke|remove)\s+(.+?)\s+(?:to|from|on)\s+(.+?)(\s+(?:with|when|if)\s+(?:auth|authed|authenticated))?$')
    @authorise
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
                event.addresponse(u"%s doesn't have that permission anyway" % username)
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

            if permission.value == value:
                event.addresponse(u"%s permission for %s is already %s" % (name, username, value))
                return

            permission.value = value
            session.save_or_update(permission)

        session.flush()
        log.info(u"%s %s permission for account %s (%s) by account %s", actions[action.lower()], name, account.id, account.username, event.account)
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
            if not auth_responses(event, u'accounts'):
                return
            account = session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is" % username)
                return

        event.addresponse(', '.join(['%s%s' % (permission_values[perm.value], perm.name) for perm in account.permissions]))

    @match(r'^list\s+permissions$')
    def list_permissions(self, event):
        permissions = []
        for processor in ibid.processors:
            if hasattr(processor, 'permission') and getattr(processor, 'permission') not in permissions:
                permissions.append(getattr(processor, 'permission'))
            if hasattr(processor, 'permissions'):
                for permission in getattr(processor, 'permissions'):
                    if permission not in permissions:
                        permissions.append(permission)

        event.addresponse(', '.join(permissions))

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
