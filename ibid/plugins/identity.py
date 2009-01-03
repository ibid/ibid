import string
from random import choice

from sqlalchemy.orm import eagerload

import ibid
from ibid.plugins import Processor, match, handler, auth_responses
from ibid.models import Account, Identity, Attribute

help = {}

help['accounts'] = 'Adds an account, which is used to link identities.'
class Accounts(Processor):
    """create account <name>"""
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
                event.addresponse(u'You already have an account called "%s".' % account.username)
                return

        account = session.query(Account).filter_by(username=username).first()
        if account:
            event.addresponse(u'There is already an account called "%s". Please choose a different name.' % account.username)
            return

        account = Account(username)
        session.add(account)
        session.commit()

        if not admin:
            identity = session.query(Identity).filter_by(id=event.identity).first()
            identity.account_id = account.id
            session.add(identity)
            session.commit()

        session.close()
        event.addresponse(u'Done')

chars = string.letters + string.digits

help['identities'] = 'Adds and removes identities from accounts.'
class Identities(Processor):
    """I am <identity> on <source>"""
    feature = 'identities'

    def __init__(self, name):
        Processor.__init__(self, name)
        self.tokens = {}

    @match(r'^(I|.+?)\s+(?:is|am)\s+(.+)\s+on\s+(.+)$')
    def identity(self, event, username, identity, source):
        session = ibid.databases.ibid()
        admin = False

        if username.upper() == 'I':
            if event.account:
                account = session.query(Account).filter_by(id=event.account).first()
            else:
                username = event.sender_id
                account = session.query(Account).filter_by(username=username).first()
                if account:
                    event.addresponse(u"I tried to create the account %s for you, but it already exists. Please use 'create account <name>'." % username)
                    return
                account = Account(username)
                session.add(account)
                session.commit()
                currentidentity = session.query(Identity).filter_by(id=event.identity).first()
                currentidentity.account_id = account.id
                session.add(currentidentity)
                session.commit()
                event.addresponse(u"I've created the account %s for you" % username)

        else:
            if not auth_responses(event, 'accounts'):
                return
            admin = True
            account = session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is" % username)
                return

        ident = session.query(Identity).filter(Identity.identity.like(identity)).filter(Identity.source.like(source)).first()
        if ident and ident.account:
            event.addresponse(u'This identity is already attached to account %s' % ident.account.username)
            return

        if not admin:
            token = ''.join([choice(chars) for i in xrange(16)])
            self.tokens[token] = (account.id, identity, source)
            response = {'reply': u'Please send me this message from %s on %s: %s' % (identity, source, token)}
            if event.public:
                response['target'] = event['sender_id']
            event.addresponse(response)

        else:
            if not ident:
                ident = Identity(source, identity)
            ident.account_id = account.id
            session.add(ident)
            session.commit()
            event.addresponse(True)

    @match(r'^(\S{16})$')
    def token(self, event, token):
        if token in self.tokens:
            session = ibid.databases.ibid()
            (account_id, user, source) = self.tokens[token]
            if event.source.lower() != source.lower() or event.sender_id.lower() != user.lower():
                event.addresponse(u'You need to send me this token from %s on %s' % (user, source))
                return

            identity = session.query(Identity).filter(Identity.identity.like(user)).filter(Identity.source.like(source)).first()
            if not identity:
                identity = Identity(source, user)
            identity.account_id = account_id
            session.add(identity)
            session.commit()
            session.close()

            del self.tokens[token]
            event.addresponse(u'Identity added')

help['attributes'] = 'Adds and removes attributes attached to an account'
class Attributes(Processor):
    """set (my|<account>) <name> to <value>"""
    feature = 'attributes'

    @match(r"^set\s+(my|.+?)(?:\'s)?\s+(.+)\s+to\s+(.+)$")
    def attribute(self, event, username, name, value):
        session = ibid.databases.ibid()

        if username.lower() == 'my':
            if not event.account:
                event.addresponse(u"I don't know who you are")
                return
            account = session.query(Account).filter_by(id=event.account).first()
            if not account:
                event.addresponse(u"%s doesn't exist. Please use 'add account' first" % username)
                return

        else:
            if not auth_responses(event, 'accounts'):
                return
            account = session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is" % username)
                return

        account.attributes.append(Attribute(name, value))
        session.add(account)
        session.commit()
        session.close()
        event.addresponse(u'Done')

class Describe(Processor):

    @match(r'^who\s+(?:is|am)\s+(I|.+?)$')
    def describe(self, event, username):
        session = ibid.databases.ibid()
        if username.upper() == 'I':
            if not event.account:
                event.addresponse(u"I don't know who you are")
                return
            account = session.query(Account).filter_by(id=event.account).first()

        else:
            account = session.query(Account).filter_by(username=username).first()
            if not account:
                event.addresponse(u"I don't know who %s is" % username)
                return

        event.addresponse(str(account))
        for identity in account.identities:
            event.addresponse(str(identity))
        for attribute in account.attributes:
            event.addresponse(str(attribute))
        session.close()

class Identify(Processor):

    priority = -1600

    def __init__(self, name):
        Processor.__init__(self, name)
        self.cache = {}

    def process(self, event):
        if 'sender_id' in event:
            #if event.sender in self.cache:
            #    (event.identity, event.account) = self.cache[event.sender]
            #    return

            session = ibid.databases.ibid()
            identity = session.query(Identity).options(eagerload('account')).filter(Identity.source.like(event.source)).filter(Identity.identity.like(event.sender_id)).first()
            if not identity:
                identity = Identity(event.source, event.sender_id)
                session.add(identity)
                session.commit()

            event.identity = identity.id
            if identity.account:
                event.account = identity.account.id
            else:
                event.account = None
            self.cache[event.sender] = (event.identity, event.account)

            session.close()

def identify(source, user):

    session = ibid.databases.ibid()

    identity = session.query(Identity).filter(Identity.source.like(source)).filter(Identity.identity.like(user)).first()
    account = session.query(Account).filter_by(username=user).first()

    if not account and not identity:
        return None
    if not account:
        return identity
    if not identity or identity in account.identities:
        return account
    return (account, identity)

# vi: set et sta sw=4 ts=4:
