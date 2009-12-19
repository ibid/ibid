from datetime import datetime
import logging

import ibid
from ibid.plugins import Processor, handler, match, authorise
from ibid.config import IntOption
from ibid.db import IbidUnicodeText, Boolean, Integer, DateTime, \
                    Table, Column, ForeignKey, relation, func
from ibid.auth import permission
from ibid.plugins.identity import get_identities
from ibid.models import Base, VersionedSchema, Identity, Account
from ibid.utils import ago, format_date

help = {'memo': u'Keeps messages for people.'}

nomemos_cache = set()
notified_overlimit_cache = set()

log = logging.getLogger('plugins.memo')

class Memo(Base):
    __table__ = Table('memos', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('from_id', Integer, ForeignKey('identities.id'), nullable=False, index=True),
    Column('to_id', Integer, ForeignKey('identities.id'), nullable=False, index=True),
    Column('memo', IbidUnicodeText, nullable=False),
    Column('private', Boolean, nullable=False),
    Column('delivered', Boolean, nullable=False, index=True),
    Column('time', DateTime, nullable=False),
    useexisting=True)

    class MemoSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.from_id)
            self.add_index(self.table.c.to_id)
            self.add_index(self.table.c.delivered)

    __table__.versioned_schema = MemoSchema(__table__, 2)

    def __init__(self, from_id, to_id, memo, private=False):
        self.from_id = from_id
        self.to_id = to_id
        self.memo = memo
        self.private = private
        self.delivered = False
        self.time = datetime.utcnow()

Identity.memos_sent = relation(Memo, primaryjoin=Identity.id==Memo.from_id, backref='sender')
Identity.memos_recvd = relation(Memo, primaryjoin=Identity.id==Memo.to_id, backref='recipient')

class Tell(Processor):
    u"""(tell|pm|privmsg|msg|ask) <person> [on <source>] <message>
    forget my (first|last|<n>th) message for <person> [on <source>]"""
    feature = 'memo'

    permission = u'sendmemo'
    permissions = (u'recvmemo',)

    @match(r'^\s*(?:please\s+)?(tell|pm|privmsg|msg|ask)\s+(\S+)\s+(?:on\s+(\S+)\s+)?(.+?)\s*$',
            version='deaddressed')
    @authorise(fallthrough=False)
    def tell(self, event, how, who, source, memo):
        source_specified = bool(source)
        if not source:
            source = event.source
        else:
            source = source.lower()

        if source.lower() == event.source and \
                [True for name in ibid.config.plugins['core']['names'] if name.lower() == who.lower()]:
            event.addresponse(u"I can't deliver messages to myself")
            return

        to = event.session.query(Identity) \
                .filter(func.lower(Identity.identity) == who.lower()) \
                .filter_by(source=source).first()

        if not to and not source_specified:
            account = event.session.query(Account) \
                    .filter(func.lower(Account.username) == who.lower()).first()
            if account:
                for identity in account.identities:
                    if identity.source == source:
                        to = identity
                if not identity:
                    identity = account.identities[0]

        if not to and not source_specified:
            event.addresponse(
                    u"I don't know who %(who)s is. "
                    u"Say '%(who)s on %(source)s' and I'll take your word that %(who)s exists", {
                    'who': who,
                    'source': source,
            })
            return

        if not to:
            if source not in ibid.sources:
                event.addresponse(u'I am not connected to %s', source)
                return
            to = Identity(source, who)
            event.session.save(to)
            event.session.commit()

            log.info(u"Created identity %s for %s on %s", to.id, to.identity, to.source)

        if permission(u'recvmemo', to.account and to.account.id or None, to.source, event.session) != 'yes':
            event.addresponse(u'Just tell %s yourself', who)
            return

        memo = u' '.join((how, who, memo))

        memo = Memo(event.identity, to.id, memo, how.lower() in (u'pm', u'privmsg', u'msg'))
        event.session.save_or_update(memo)

        event.session.commit()
        log.info(u"Stored memo %s for %s (%s) from %s (%s): %s",
                memo.id, to.id, who, event.identity, event.sender['connection'], memo.memo)
        event.memo = memo.id
        nomemos_cache.clear()
        notified_overlimit_cache.discard(to.id)

        event.addresponse(True)

    @match(r'^(?:delete|forget)\s+(?:my\s+)?'
            r'(?:(first|last|\d+(?:st|nd|rd|th)?)\s+)?' # 1st way to specify number
            r'(?:memo|message|msg)\s+'
            r'(?(1)|#?(\d+)\s+)?' # 2nd way
            r'(?:for|to)\s+(.+?)(?:\s+on\s+(\S+))?$')
    @authorise(fallthrough=False)
    def forget(self, event, num1, num2, who, source):
        if not source:
            source = event.source
        else:
            source = source.lower()
        number = num1 or num2 or 'last'
        number = number.lower()
        if number == 0:
            # Don't wrap around to last message, that'd be unexpected
            number = 1
        elif number.isdigit():
            number = int(number) - 1
        elif number == 'first':
            number = 0
        elif number == 'last':
            number = -1
        else:
            number = int(number[:-2]) - 1

        # Join on column x isn't possible in SQLAlchemy 0.4:
        identities_to = event.session.query(Identity) \
                .filter_by(source=source) \
                .filter(func.lower(Identity.identity) == who.lower()) \
                .all()

        identities_to = [identity.id for identity in identities_to]

        memos = event.session.query(Memo) \
                .filter_by(delivered=False) \
                .filter_by(from_id=event.identity) \
                .filter(Memo.to_id.in_(identities_to)) \
                .order_by(Memo.time.asc())
        count = memos.count()

        if not count:
            event.addresponse(
                    u"You don't have any outstanding messages for %(who)s on %(source)s", {
                        'who': who,
                        'source': source,
                })
            return

        if abs(number) > count:
            event.addresponse(
                    u"That memo does not exist, you only have %(count)i outstanding memos for %(who)s on %(source)s", {
                        'count': count,
                        'who': who,
                        'source': source,
            })
            return

        if number == -1:
            number = count - 1

        memo = memos[number]

        event.session.delete(memo)
        event.session.commit()
        log.info(u"Cancelled memo %s for %s (%s) from %s (%s): %s",
                memo.id, memo.to_id, who, event.identity, event.sender['connection'], memo.memo)

        if count > 1:
            event.addresponse(
                    u"Forgotten memo %(number)i for %(who)s on %(source)s, but you still have %(count)i pending", {
                        'number': number,
                        'who': who,
                        'source': source,
                        'count': count - 1,
            })
        else:
            event.addresponse(True)

def get_memos(event, delivered=False):
    identities = get_identities(event)
    return event.session.query(Memo) \
            .filter_by(delivered=delivered) \
            .filter(Memo.to_id.in_(identities)) \
            .order_by(Memo.time.asc()).all()

class Deliver(Processor):
    feature = 'memo'

    addressed = False
    processed = True

    public_limit = IntOption('public_limit', 'Maximum number of memos to read out in public (flood-protection)', 2)

    @handler
    def deliver(self, event):
        if event.identity in nomemos_cache:
            return

        memos = get_memos(event)

        if len(memos) > self.public_limit and event.public:
            if event.identity not in notified_overlimit_cache:
                public = [True for memo in memos if not memo.private]
                message = u'By the way, you have a pile of memos waiting for you, too many to read out in public. PM me'
                if public:
                    event.addresponse(u'%s: ' + message, event.sender['nick'])
                else:
                    event.addresponse(message, target=event.sender['connection'])
                notified_overlimit_cache.add(event.identity)
            return

        for memo in memos:
            # Don't deliver if the user just sent a memo to themself
            if 'memo' in event and event.memo == memo.id:
                continue

            if memo.private:
                message = u'By the way, %(sender)s on %(source)s told me "%(message)s" %(ago)s ago' % {
                    'sender': memo.sender.identity,
                    'source': memo.sender.source,
                    'message': memo.memo,
                    'ago': ago(event.time - memo.time),
                }
                event.addresponse(message, target=event.sender['connection'])
            else:
                event.addresponse(u'By the way, %(sender)s on %(source)s told me "%(message)s" %(ago)s ago', {
                    'sender': memo.sender.identity,
                    'source': memo.sender.source,
                    'message': memo.memo,
                    'ago': ago(event.time - memo.time),
                })

            memo.delivered = True
            event.session.save_or_update(memo)
            event.session.commit()
            log.info(u"Delivered memo %s to %s (%s)",
                    memo.id, event.identity, event.sender['connection'])

        if 'memo' not in event:
            nomemos_cache.add(event.identity)

class Notify(Processor):
    feature = 'memo'

    event_types = ('state',)
    addressed = False
    processed = True

    public_limit = IntOption('public_limit', 'Maximum number of memos to read out in public (flood-protection)', 2)

    @handler
    def state(self, event):
        if event.state != 'online':
            return

        if event.identity in nomemos_cache:
            return

        memos = get_memos(event)

        if len(memos) > self.public_limit:
            event.addresponse(
                u'You have %s messages, too many for me to tell you in public,'
                u' so ask me in private.',
                len(memos), target=event.sender['connection'])
        elif len(memos) > 0:
            event.addresponse(u'You have %s messages', len(memos),
                target=event.sender['connection'])
        else:
            nomemos_cache.add(event.identity)

class Messages(Processor):
    u"""my messages
    message <number>
    my messages for <person> [on <source>]"""
    feature = 'memo'

    @match(r'^my\s+messages$')
    def messages(self, event):
        memos = get_memos(event, True)
        if memos:
            event.addresponse(u', '.join(
                '%s: %s (%s)' % (
                    memos.index(memo) + 1,
                    memo.sender.identity,
                    format_date(memo.time),
                ) for memo in memos
            ))
        else:
            event.addresponse(u"Sorry, nobody loves you")

    @match(r'^my\s+messages\s+(?:for|to)\s+(.+?)(?:\s+on\s+(\S+))?$')
    def messages_for(self, event, who, source):
        identities = get_identities(event)

        if not source:
            source = event.source
        else:
            source = source.lower()

        # Join on column x isn't possible in SQLAlchemy 0.4:
        identities_to = event.session.query(Identity) \
                .filter_by(source=source) \
                .filter(func.lower(Identity.identity) == who.lower()) \
                .all()

        identities_to = [identity.id for identity in identities_to]

        memos = event.session.query(Memo) \
                .filter_by(delivered=False) \
                .filter(Memo.from_id.in_(identities)) \
                .filter(Memo.to_id.in_(identities_to)) \
                .order_by(Memo.time.asc()).all()

        if memos:
            event.addresponse(u'Pending: ' + u', '.join(
                '%i: %s (%s)' % (i + 1, memo.memo, format_date(memo.time))
                for i, memo in enumerate(memos)
            ))
        else:
            event.addresponse(u"Sorry, all your memos to %(who)s on %(source)s are already delivered", {
                'who': who,
                'source': source,
            })

    @match(r'^message\s+(\d+)$')
    def message(self, event, number):
        memos = get_memos(event, True)

        number = int(number) - 1
        if number >= len(memos) or number == -1:
            event.addresponse(u'Sorry, no such message in your archive')
            return

        memo = memos[number]

        event.addresponse(u"From %(sender)s on %(source)s at %(time)s: %(message)s", {
            'sender': memo.sender.identity,
            'source': memo.sender.source,
            'time': format_date(memo.time),
            'message': memo.memo,
        })

# vi: set et sta sw=4 ts=4:
