# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import string
from random import choice
import logging

import ibid
from ibid.config import Option
from ibid.compat import any
from ibid.db import eagerload, IntegrityError, and_, or_
from ibid.db.models import Account, Identity, Attribute, Credential, Permission
from ibid.plugins import Processor, match, handler, auth_responses, authorise
from ibid.utils import human_join
from ibid.auth import hash

features = {}
identify_cache = {}

log = logging.getLogger('plugins.identity')

features['accounts'] = {
    'description': u'Manage users accounts with the bot. An account represents '
                   u'a person. An account has one or more identities, which is '
                   u'a user on a specific source.',
    'categories': ('admin', 'account',),
}
class Accounts(Processor):
    u"""create account [<name>]
    delete (my account|account <name>)
    rename (my account|account <name>) to <name>"""
    feature = ('accounts',)

    @match(r'^create\s+account(?:\s+(.+))?$')
    def new_account(self, event, username):
        admin = False

        if event.account:
            if ibid.auth.authenticate(event) and ibid.auth.authorise(event, 'accounts'):
                admin = True
            else:
                account = event.session.query(Account).get(event.account)
                event.addresponse(u'You already have an account called "%s"', account.username)
                return

        if not username:
            identity = event.session.query(Identity).get(event.identity)
            username = identity.identity

        account = event.session.query(Account).filter_by(username=username).first()
        if account:
            event.addresponse(u'There is already an account called "%s". ' \
                    'Please choose a different name', account.username)
            return

        account = Account(username)
        event.session.save_or_update(account)
        event.session.commit()
        log.info(u"Created account %s (%s) by %s/%s (%s)",
                account.id, account.username, event.account, event.identity, event.sender['connection'])

        if admin:
            identity = event.session.query(Identity) \
                    .filter_by(identity=username, source=event.source).first()
            if identity:
                identity.account_id = account.id
                event.session.save_or_update(identity)
                event.session.commit()
                log.info(u"Attached identity %s (%s on %s) to account %s (%s)",
                        identity.id, identity.identity, identity.source, account.id, account.username)
        else:
            identity = event.session.query(Identity).get(event.identity)
            identity.account_id = account.id
            event.session.save_or_update(identity)
            event.session.commit()
            log.info(u"Attached identity %s (%s on %s) to account %s (%s)",
                    identity.id, identity.identity, identity.source, account.id, account.username)

        identify_cache.clear()
        event.addresponse(True)

    @match(r'^delete\s+(?:(my)\s+account|account\s+(.+))$')
    def del_account(self, event, own, username):
        admin = False

        if own:
            if event.account:
                account = event.session.query(Account).get(event.account)
            else:
                event.addresponse(u"You don't have an account")
                return
        else:
            if ibid.auth.authenticate(event) and ibid.auth.authorise(event, 'accounts'):
                admin = True
            account = event.session.query(Account).filter_by(username=username).first()
            if not account:
                if admin:
                    event.addresponse(u"Sorry, no such account")
                return
            elif not admin or username != account.username:
                return

        event.session.delete(account)
        event.session.commit()
        identify_cache.clear()

        log.info(u"Deleted account %s (%s) by %s/%s (%s)",
                account.id, account.username, event.account, event.identity, event.sender['connection'])
        event.addresponse(True)

    @match(r'^rename\s+(?:(my)\s+account|account\s+(.+))\s+to\s+(.+)$')
    def ren_account(self, event, own, username, newname):
        admin = False

        if own:
            if event.account:
                account = event.session.query(Account).get(event.account)
            else:
                event.addresponse(u"You don't have an account")
                return
        else:
            if ibid.auth.authenticate(event) and ibid.auth.authorise(event, 'accounts'):
                admin = True
            account = event.session.query(Account).filter_by(username=username).first()
            if not account:
                if admin:
                    event.addresponse(u"Sorry, no such account")
                return
            elif not admin and username != account.username:
                return

        oldname = account.username
        account.username = newname

        event.session.save_or_update(account)
        event.session.commit()
        identify_cache.clear()

        log.info(u"Renamed account %s (%s) to %s by %s/%s (%s)",
                account.id, oldname, account.username, event.account, event.identity, event.sender['connection'])
        event.addresponse(True)

# Don't include possibly ambiguous characters:
chars = [x for x in string.letters + string.digits if x not in '01lOIB86G']

class Identities(Processor):
    u"""(I am|<username> is) <identity> on <source>
    remove identity <identity> on <source> [from <username>]"""
    feature = ('accounts',)
    priority = -10

    def __init__(self, name):
        Processor.__init__(self, name)
        self.tokens = {}

    @match(r'^(I|.+?)\s+(?:is|am)\s+(.+)\s+on\s+(.+)$')
    def identity(self, event, username, identity, source):
        admin = False
        identity = identity.replace(' ', '')
        reverse_attach = False

        if username.upper() == 'I':
            if event.account:
                account = event.session.query(Account).get(event.account)
            else:
                account = event.session.query(Account) \
                        .join('identities') \
                        .filter(Identity.identity == identity) \
                        .filter(Identity.source == source).first()

                if account:
                    reverse_attach = True
                else:
                    username = event.sender['id']

                    account = event.session.query(Account) \
                            .filter_by(username=username).first()

                    if account:
                        event.addresponse(u'I tried to create the account %s for you, but it already exists. '
                            u"Please use 'create account <name>'", username)
                        return

                    account = Account(username)
                    event.session.save_or_update(account)

                    currentidentity = event.session.query(Identity) \
                            .get(event.identity)
                    currentidentity.account_id = account.id
                    event.session.save_or_update(currentidentity)

                    identify_cache.clear()

                    event.addresponse(u"I've created the account %s for you", username)

                    event.session.commit()
                    log.info(u"Created account %s (%s) by %s/%s (%s)",
                            account.id, account.username, event.account, event.identity, event.sender['connection'])
                    log.info(u"Attached identity %s (%s on %s) to account %s (%s)",
                            currentidentity.id, currentidentity.identity, currentidentity.source, account.id, account.username)

        else:
            if not auth_responses(event, 'accounts'):
                return
            admin = True
            account = event.session.query(Account) \
                    .filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is", username)
                return

        if reverse_attach:
            ident = event.session.query(Identity).get(event.identity)
        else:
            ident = event.session.query(Identity) \
                    .filter_by(identity=identity, source=source).first()
        if ident and ident.account:
            event.addresponse(u'This identity is already attached to account %s',
                    ident.account.username)
            return

        if source not in ibid.sources:
            event.addresponse(u'I am not connected to %s', source)
            return
        else:
            source = ibid.sources[source].name

        if not admin:
            token = ''.join([choice(chars) for i in xrange(16)])
            if reverse_attach:
                self.tokens[token] = (account.id, ident.identity, ident.source)
                response = {
                        'reply': u'Please send me this message from %s on %s: %s' % (ident.identity, ident.source, token),
                        'target': identity,
                        'source': source,
                }
                event.addresponse(True)
            else:
                self.tokens[token] = (account.id, identity, source)
                response = {'reply': u'Please send me this message from %s on %s: %s' % (identity, source, token)}
                if event.public:
                    response['target'] = event.sender['id']
                    event.addresponse(True)
            event.addresponse(response)
            log.info(u"Sent token %s to %s/%s (%s)",
                    token, event.account, event.identity, event.sender['connection'])

        else:
            if not ident:
                ident = Identity(source, identity)
            ident.account_id = account.id
            event.session.save_or_update(ident)
            event.session.commit()

            identify_cache.clear()

            event.addresponse(True)
            log.info(u"Attached identity %s (%s on %s) to account %s (%s) by %s/%s (%s)",
                    ident.id, ident.identity, ident.source, account.id, account.username,
                    event.account, event.identity, event.sender['connection'])

    @match(r'^(\S{16})$')
    def token(self, event, token):
        if token in self.tokens:
            (account_id, user, source) = self.tokens[token]
            if event.source.lower() != source.lower() or event.sender['id'].lower() != user.lower():
                event.addresponse(u'You need to send me this token from %(name)s on %(source)s', {
                    'name': user,
                    'source': source,
                })
                return

            identity = event.session.query(Identity) \
                    .filter_by(identity=user, source=source).first()
            if not identity:
                identity = Identity(source, user)
            identity.account_id = account_id
            event.session.save_or_update(identity)
            identify_cache.clear()

            del self.tokens[token]
            event.session.commit()

            event.addresponse(u'Identity added')

            log.info(u"Attached identity %s (%s on %s) to account %s by %s/%s (%s) with token %s",
                    identity.id, identity.identity, identity.source, account_id, event.account,
                    event.identity, event.sender['connection'], token)

    @match(r'^remove\s+identity\s+(.+?)\s+on\s+(\S+)(?:\s+from\s+(\S+))?$')
    def remove(self, event, user, source, username):
        if not username:
            account = event.session.query(Account).get(event.account)
        else:
            if not auth_responses(event, 'accounts'):
                return
            account = event.session.query(Account) \
                    .filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is", username)
                return

        identity = event.session.query(Identity) \
                .filter_by(account_id=account.id, identity=user,
                           source=source).first()
        if not identity:
            event.addresponse(u"I don't know about that identity")
        else:
            identity.account_id = None
            event.session.save_or_update(identity)
            event.session.commit()

            identify_cache.clear()

            event.addresponse(True)
            log.info(u"Removed identity %s (%s on %s) from account %s (%s) by %s/%s (%s)",
                    identity.id, identity.identity, identity.source, account.id,
                    account.username, event.account, event.identity, event.sender['connection'])

class Attributes(Processor):
    u"""set (my|<account>) <name> to <value>"""
    feature = ('accounts',)

    @match(r"^set\s+(my|.+?)(?:\'s)?\s+(.+)\s+to\s+(.+)$")
    def attribute(self, event, username, name, value):

        if username.lower() == 'my':
            if not event.account:
                event.addresponse(u"I don't know who you are")
                return
            account = event.session.query(Account).get(event.account)
            if not account:
                event.addresponse(u"%s doesn't exist. Please use 'add account' first", username)
                return

        else:
            if not auth_responses(event, 'accounts'):
                return
            account = event.session.query(Account) \
                    .filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is", username)
                return

        account.attributes.append(Attribute(name, value))
        event.session.save_or_update(account)
        event.session.commit()

        event.addresponse(True)
        log.info(u"Added attribute '%s' = '%s' to account %s (%s) by %s/%s (%s)",
                name, value, account.id, account.username, event.account,
                event.identity, event.sender['connection'])

class Describe(Processor):
    u"""who (am I|is <username>)"""
    feature = ('accounts',)

    @match(r'^who\s+(?:is|am)\s+(I|.+?)$')
    def describe(self, event, username):
        if username.upper() == 'I':
            if not event.account:
                identity = event.session.query(Identity).get(event.identity)
                event.addresponse(u"%(name)s on %(source)s", {
                    'name': identity.identity,
                    'source': identity.source,
                })
                return
            account = event.session.query(Account).get(event.account)

        else:
            account = event.session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is", username)
                return

        event.addresponse(u'%(accountname)s is %(identities)s', {
            'accountname': account.username,
            'identities': human_join(u'%s on %s' % (identity.identity, identity.source) for identity in account.identities),
        })

features['summon'] = {
    'description': u'Get the attention of a person via different source',
    'categories': ('message',),
}
class Summon(Processor):
    u"summon <person> [via <source>]"
    feature = ('summon',)
    permission = u'summon'

    default_source = Option('default_source',
            u'Default source to summon people via', u'jabber')

    @authorise(fallthrough=False)
    @match(r'^summon\s+(\S+)(?:\s+(?:via|on|using)\s+(\S+))?$')
    def summon(self, event, who, source):
        if not source:
            source = self.default_source

        if source.lower() not in ibid.sources:
            event.addresponse(u"I'm afraid that I'm not connected to %s",
                              source)
            return

        account = event.session.query(Account) \
            .options(eagerload('identities')) \
            .join('identities') \
            .filter(
                or_(
                    and_(
                        Identity.identity == who,
                        Identity.source == event.source,
                    ),
                    Account.username == who,
                )) \
            .first()

        if account:
            for other_identity in [id for id
                    in account.identities
                    if id.source.lower() == source.lower()]:
                if any(True for channel
                        in ibid.channels[other_identity.source].itervalues()
                        if other_identity.id in channel):
                    event.addresponse(u'Your presence has been requested by '
                                      u'%(who)s in %(channel)s on %(source)s.',
                        {
                            'who': event.sender['nick'],
                            'channel': (not event.public)
                                    and u'private' or event.channel,
                            'source': event.source,
                        }, target=other_identity.identity,
                        source=other_identity.source, address=False)
                    event.addresponse(True)
                else:
                    event.addresponse(
                        u"Sorry %s doesn't appear to be available right now.",
                        who)
                return

        event.addresponse(
                u"Sorry, I don't know how to find %(who)s on %(source)s. "
                u'%(who)s must first link an identity on %(source)s.', {
                    'who': who,
                    'source': source,
        })
        return

class Identify(Processor):

    priority = -1600
    addressed = False
    processed = True
    event_types = (u'message', u'state', u'action', u'notice')

    @handler
    def handle(self, event):
        if event.sender:
            if (event.source, event.sender['connection']) in identify_cache:
                (event.identity, event.account) = identify_cache[(event.source, event.sender['connection'])]
                return

            identity = event.session.query(Identity) \
                    .options(eagerload('account')) \
                    .filter_by(source=event.source,
                               identity=event.sender['id']) \
                    .first()
            if not identity:
                identity = Identity(event.source, event.sender['id'])
                event.session.save_or_update(identity)
                try:
                    event.session.commit()
                    log.info(u'Created identity %s for %s on %s', identity.id, identity.identity, identity.source)
                except IntegrityError:
                    event.session.rollback()
                    event.session.close()
                    del event['session']
                    log.debug(u'Race encountered creating identity for %s on %s', event.sender['id'], event.source)
                    identity = event.session.query(Identity) \
                            .options(eagerload('account')) \
                            .filter_by(source=event.source,
                                       identity=event.sender['id']) \
                            .one()

            event.identity = identity.id
            if identity.account:
                event.account = identity.account.id
            else:
                event.account = None
            identify_cache[(event.source, event.sender['connection'])] = (event.identity, event.account)

def get_identities(event):
    if event.account:
        account = event.session.query(Account).get(event.account)
        return [identity.id for identity in account.identities]
    else:
        return (event.identity,)

def identify(session, source, id):
    identity = session.query(Identity) \
                      .filter_by(source=source, identity=id).first()
    return identity and identity.id

actions = {'revoke': 'Revoked', 'grant': 'Granted', 'remove': 'Removed'}

features['auth'] = {
    'description': u'Adds and removes authentication credentials and '
                   u'permissions',
    'categories': ('admin', 'account',),
}
class AddAuth(Processor):
    u"""authenticate <account> [on source] using <method> [<credential>]"""
    feature = ('auth',)

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
    feature = ('auth',)

    permission = u'admin'

    @match(r'^(grant|revoke|remove)\s+(.+?)(?:\s+permission)?\s+(?:to|from|on)\s+(.+?)(\s+(?:with|when|if)\s+(?:auth|authed|authenticated))?$')
    @authorise()
    def grant(self, event, action, name, username, auth):

        account = event.session.query(Account).filter_by(username=username).first()
        if not account:
            event.addresponse(u"I don't know who %s is", username)
            return

        permission = event.session.query(Permission) \
                .filter_by(account_id=account.id, name=name).first()
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
            account = event.session.query(Account) \
                    .filter_by(username=username).first()
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
    feature = ('auth',)

    @match(r'^auth(?:\s+(.+))?$')
    def handler(self, event, password):
        result = ibid.auth.authenticate(event, password)
        if result:
            event.addresponse(u'You are authenticated')
        else:
            event.addresponse(u'Authentication failed')


# vi: set et sta sw=4 ts=4:
