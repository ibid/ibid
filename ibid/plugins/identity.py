import string
from random import choice
import logging

from sqlalchemy.orm import eagerload
from sqlalchemy.sql import func
from sqlalchemy.exceptions import IntegrityError

import ibid
from ibid.plugins import Processor, match, auth_responses
from ibid.models import Account, Identity, Attribute

help = {}
identify_cache = {}

log = logging.getLogger('plugins.identity')

help['accounts'] = u'An account represents a person. An account has one or more identities, which is a user on a specific source.'
class Accounts(Processor):
    u"""create account <name>"""
    feature = 'accounts'

    @match(r'^create\s+account\s+(.+)$')
    def account(self, event, username):
        session = ibid.databases.ibid()
        admin = False

        if event.account:
            if ibid.auth.authenticate(event) and ibid.auth.authorise(event, 'accounts'):
                admin = True
            else:
                account = session.query(Account).filter_by(id=event.account).first()
                event.addresponse(u'You already have an account called "%s"', account.username)
                return

        account = session.query(Account).filter_by(username=username).first()
        if account:
            event.addresponse(u'There is already an account called "%s". Please choose a different name', account.username)
            return

        account = Account(username)
        session.save_or_update(account)
        session.flush()
        log.info(u"Created account %s (%s) by %s/%s (%s)", account.id, account.username, event.account, event.identity, event.sender['connection'])

        if not admin:
            identity = session.query(Identity).filter_by(id=event.identity).first()
            identity.account_id = account.id
            session.save_or_update(identity)
            session.flush()
            log.info(u"Attached identity %s (%s on %s) to account %s (%s)", identity.id, identity.identity, identity.source, account.id, account.username)

        identify_cache.clear()
        session.close()
        event.addresponse(True)

chars = string.letters + string.digits

class Identities(Processor):
    u"""(I am|<username> is) <identity> on <source>
    remove identity <identity> on <source> [from <username>]"""
    feature = 'accounts'
    priority = -10

    def __init__(self, name):
        Processor.__init__(self, name)
        self.tokens = {}

    @match(r'^(I|.+?)\s+(?:is|am)\s+(.+)\s+on\s+(.+)$')
    def identity(self, event, username, identity, source):
        session = ibid.databases.ibid()
        admin = False
        identity = identity.replace(' ', '')

        if username.upper() == 'I':
            if event.account:
                account = session.query(Account).filter_by(id=event.account).first()
            else:
                username = event.sender['id']
                account = session.query(Account).filter_by(username=username).first()
                if account:
                    event.addresponse(u'I tried to create the account %s for you, but it already exists. '
                        u"Please use 'create account <name>'", username)
                    return
                account = Account(username)
                session.save_or_update(account)
                session.flush()
                currentidentity = session.query(Identity).filter_by(id=event.identity).first()
                currentidentity.account_id = account.id
                session.save_or_update(currentidentity)
                session.flush()
                identify_cache.clear()
                event.addresponse(u"I've created the account %s for you", username)
                log.info(u"Created account %s (%s) by %s/%s (%s)", account.id, account.username, event.account, event.identity, event.sender['connection'])
                log.info(u"Attached identity %s (%s on %s) to account %s (%s)", currentidentity.id, currentidentity.identity, currentidentity.source, account.id, account.username)

        else:
            if not auth_responses(event, 'accounts'):
                return
            admin = True
            account = session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is", username)
                return

        ident = session.query(Identity).filter(func.lower(Identity.identity)==identity.lower()).filter(func.lower(Identity.source)==source.lower()).first()
        if ident and ident.account:
            event.addresponse(u'This identity is already attached to account %s', ident.account.username)
            return

        if source not in ibid.sources:
            event.addresponse(u'I am not connected to %s', source)
            return
        else:
            source = ibid.sources[source].name

        if not admin:
            token = ''.join([choice(chars) for i in xrange(16)])
            self.tokens[token] = (account.id, identity, source)
            response = {'reply': u'Please send me this message from %s on %s: %s' % (identity, source, token)}
            if event.public:
                response['target'] = event.sender['id']
            event.addresponse(response)
            log.info(u"Sent token %s to %s/%s (%s)", token, event.account, event.identity, event.sender['connection'])

        else:
            if not ident:
                ident = Identity(source, identity)
            ident.account_id = account.id
            session.save_or_update(ident)
            session.flush()
            identify_cache.clear()
            event.addresponse(True)
            log.info(u"Attached identity %s (%s on %s) to account %s (%s) by %s/%s (%s)", ident.id, ident.identity, ident.source, account.id, account.username, event.account, event.identity, event.sender['connection'])

    @match(r'^(\S{16})$')
    def token(self, event, token):
        if token in self.tokens:
            session = ibid.databases.ibid()
            (account_id, user, source) = self.tokens[token]
            if event.source.lower() != source.lower() or event.sender['id'].lower() != user.lower():
                event.addresponse(u'You need to send me this token from %(name)s on %(source)s', {
                    'name': user,
                    'source': source,
                })
                return

            identity = session.query(Identity).filter(func.lower(Identity.identity)==user.lower()).filter(func.lower(Identity.source)==source.lower()).first()
            if not identity:
                identity = Identity(source, user)
            identity.account_id = account_id
            session.save_or_update(identity)
            session.flush()
            session.close()
            identify_cache.clear()

            del self.tokens[token]
            event.addresponse(u'Identity added')
            log.info(u"Attached identity %s (%s on %s) to account %s by %s/%s (%s) with token %s", identity.id, identity.identity, identity.source, account_id, event.account, event.identity, event.sender['connection'], token)

    @match(r'^remove\s+identity\s+(.+?)\s+on\s+(\S+)(?:\s+from\s+(\S+))?$')
    def remove(self, event, user, source, username):
        session = ibid.databases.ibid()

        if not username:
            account = session.query(Account).get(event.account)
        else:
            if not auth_responses(event, 'accounts'):
                return
            account = session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is", username)
                return

        identity = session.query(Identity).filter_by(account_id=account.id).filter(func.lower(Identity.identity)==user.lower()).filter(func.lower(Identity.source)==source.lower()).first()
        if not identity:
            event.addresponse(u"I don't know about that identity")
        else:
            identity.account_id = None
            session.save_or_update(identity)
            session.flush()
            identify_cache.clear()
            event.addresponse(True)
            log.info(u"Removed identity %s (%s on %s) from account %s (%s) by %s/%s (%s)", identity.id, identity.identity, identity.source, account.id, account.username, event.account, event.identity, event.sender['connection'])

        session.close()

class Attributes(Processor):
    u"""set (my|<account>) <name> to <value>"""
    feature = 'accounts'

    @match(r"^set\s+(my|.+?)(?:\'s)?\s+(.+)\s+to\s+(.+)$")
    def attribute(self, event, username, name, value):
        session = ibid.databases.ibid()

        if username.lower() == 'my':
            if not event.account:
                event.addresponse(u"I don't know who you are")
                return
            account = session.query(Account).filter_by(id=event.account).first()
            if not account:
                event.addresponse(u"%s doesn't exist. Please use 'add account' first", username)
                return

        else:
            if not auth_responses(event, 'accounts'):
                return
            account = session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is", username)
                return

        account.attributes.append(Attribute(name, value))
        session.save_or_update(account)
        session.flush()
        session.close()
        event.addresponse(True)
        log.info(u"Added attribute '%s' = '%s' to account %s (%s) by %s/%s (%s)", name, value, account.id, account.username, event.account, event.identity, event.sender['connection'])

class Describe(Processor):
    u"""who (am I|is <username>)"""
    feature = "accounts"

    @match(r'^who\s+(?:is|am)\s+(I|.+?)$')
    def describe(self, event, username):
        session = ibid.databases.ibid()
        if username.upper() == 'I':
            if not event.account:
                identity = session.query(Identity).get(event.identity)
                event.addresponse(u"%(name)s on %(source)s", {
                    'name': identity.identity,
                    'source': identity.source,
                })
                return
            account = session.query(Account).get(event.account)

        else:
            account = session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is", username)
                return

        event.addresponse(u'%(accountname)s is %(identities)s', {
            'accountname': account.username,
            'identities': u', '.join(u'%s on %s' % (identity.identity, identity.source) for identity in account.identities),
        })
        session.close()

class Identify(Processor):

    priority = -1600

    def process(self, event):
        if event.sender:
            if (event.source, event.sender['connection']) in identify_cache:
                (event.identity, event.account) = identify_cache[(event.source, event.sender['connection'])]
                return

            session = ibid.databases.ibid()
            identity = session.query(Identity)\
                    .options(eagerload('account'))\
                    .filter(func.lower(Identity.source) == event.source.lower())\
                    .filter(func.lower(Identity.identity) == event.sender['id'].lower())\
                    .first()
            if not identity:
                identity = Identity(event.source, event.sender['id'])
                session.save_or_update(identity)
                try:
                    session.flush()
                    log.info(u'Created identity %s for %s on %s', identity.id, identity.identity, identity.source)
                except IntegrityError:
                    session.expunge(identity)
                    log.debug(u'Race encountered creating identity for %s on %s', event.sender['id'], event.source)
                    identity = session.query(Identity)\
                            .options(eagerload('account'))\
                            .filter(func.lower(Identity.source) == event.source.lower())\
                            .filter(func.lower(Identity.identity) == event.sender['id'].lower())\
                            .one()

            event.identity = identity.id
            if identity.account:
                event.account = identity.account.id
            else:
                event.account = None
            identify_cache[(event.source, event.sender['connection'])] = (event.identity, event.account)

            session.close()

def identify(source, user):

    session = ibid.databases.ibid()

    identity = session.query(Identity).filter(func.lower(Identity.source)==source.lower()).filter(func.lower(Identity.identity)==user.lower()).first()
    account = session.query(Account).filter_by(username=user).first()

    if not account and not identity:
        return None
    if not account:
        return identity
    if not identity or identity in account.identities:
        return account
    return (account, identity)

def get_identities(event, session=None):
    if not session:
        session = ibid.databases.ibid()

    if event.account:
        account = session.query(Account).get(event.account)
        return [identity.id for identity in account.identities]
    else:
        return (event.identity,)

# vi: set et sta sw=4 ts=4:
