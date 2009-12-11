import logging

from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match, auth_responses, authorise
from ibid.models import Credential, Permission, Account
from ibid.auth import hash
from ibid.utils import human_join

help = {}

log = logging.getLogger('plugins.auth')

actions = {'revoke': 'Revoked', 'grant': 'Granted', 'remove': 'Removed'}

help['auth'] = u'Adds and removes authentication credentials and permissions'
class AddAuth(Processor):
    u"""authenticate <account> [on source] using <method> [<credential>]"""
    feature = 'auth'

    @match(r'^authenticate\s+(.+?)(?:\s+on\s+(.+))?\s+using\s+(\S+)\s+(.+)$')
    def handler(self, event, user, source, method, credential):

        if user.lower() == 'me':
            if not event.account:
                event.addresponse(u"I don't know who you are")
                return
            if not ibid.auth.authenticate(event):
                event.complain = 'notauthed'
                return
            account = event.session.query(Account).get(event.account)

        else:
            if not auth_responses(event, 'admin'):
                return
            account = event.session.query(Account).filter_by(username=user).first()
            if not account:
                event.addresponse(u"I don't know who %s is", user)
                return

        if source:
            if source not in ibid.sources:
                event.addresponse(u"I am not connected to %s", source)
                return
            source = ibid.sources[source].name

        if method.lower() == 'password':
            password = hash(credential)
            event.message['clean'] = event.message['clean'][:-len(credential)] + password
            event.message['raw'] = event.message['raw'][:event.message['raw'].rfind(credential)] \
                    + password + event.message['raw'][event.message['raw'].rfind(credential)+len(credential):]
            credential = password

        credential = Credential(method, credential, source, account.id)
        event.session.save_or_update(credential)
        event.session.commit()
        log.info(u"Added %s credential %s for account %s (%s) on %s by account %s",
                method, credential.credential, account.id, account.username, source, event.account)

        event.addresponse(True)

permission_values = {'no': '-', 'yes': '+', 'auth': ''}
class Permissions(Processor):
    u"""(grant|revoke|remove) <permission> (to|from|on) <username> [when authed]
    permissions [for <username>]
    list permissions"""
    feature = 'auth'

    permission = u'admin'

    @match(r'^(grant|revoke|remove)\s+(.+?)(?:\s+permission)?\s+(?:to|from|on)\s+(.+?)(\s+(?:with|when|if)\s+(?:auth|authed|authenticated))?$')
    @authorise()
    def grant(self, event, action, name, username, auth):

        account = event.session.query(Account).filter_by(username=username).first()
        if not account:
            event.addresponse(u"I don't know who %s is", username)
            return

        permission = event.session.query(Permission) \
                .filter_by(account_id=account.id) \
                .filter(func.lower(Permission.name) == name.lower()).first()
        if action.lower() == 'remove':
            if permission:
                event.session.delete(permission)
            else:
                event.addresponse(u"%s doesn't have that permission anyway", username)
                return

        else:
            if not permission:
                permission = Permission(name)
                account.permissions.append(permission)

            if action.lower() == 'revoke':
                value = 'no'
            elif auth:
                value = 'auth'
            else:
                value = 'yes'

            if permission.value == value:
                event.addresponse(u'%(permission)s permission for %(user)s is already %(value)s', {
                    'permission': name,
                    'user': username,
                    'value': value,
                })
                return

            permission.value = value
            event.session.save_or_update(permission)

        event.session.commit()
        ibid.auth.drop_caches()
        log.info(u"%s %s permission for account %s (%s) by account %s",
                actions[action.lower()], name, account.id, account.username, event.account)

        event.addresponse(True)

    @match(r'^permissions(?:\s+for\s+(\S+))?$')
    def list(self, event, username):
        if not username:
            if not event.account:
                event.addresponse(u"I don't know who you are")
                return
            account = event.session.query(Account).get(event.account)
        else:
            if not auth_responses(event, u'accounts'):
                return
            account = event.session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is", username)
                return

        permissions = sorted(u'%s%s' % (permission_values[perm.value], perm.name) for perm in account.permissions)
        event.addresponse(u'Permissions: %s', human_join(permissions) or u'none')

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

        event.addresponse(u'Permissions: %s', human_join(sorted(permissions)) or u'none')

class Auth(Processor):
    u"""auth <credential>"""
    feature = 'auth'

    @match(r'^auth(?:\s+(.+))?$')
    def handler(self, event, password):
        result = ibid.auth.authenticate(event, password)
        if result:
            event.addresponse(u'You are authenticated')
        else:
            event.addresponse(u'Authentication failed')

# vi: set et sta sw=4 ts=4:
