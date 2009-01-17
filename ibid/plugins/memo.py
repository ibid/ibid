from datetime import datetime
import logging

from sqlalchemy import Column, Integer, Unicode, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, handler, match, authorise
from ibid.plugins.auth import permission
from ibid.plugins.identity import get_identities
from ibid.models import Identity, Account, Memo
from ibid.utils import ago

help = {'memo': 'Keeps messages for people.'}

memo_cache = {}
log = logging.getLogger('plugins.memo')

class Tell(Processor):
    """(tell|pm|privmsg|msg) <person> <message>"""
    feature = 'memo'

    permission = u'sendmemo'
    permissions = (u'recvmemo',)

    @match(r'^(?:please\s+)?(tell|pm|privmsg|msg)\s+(\S+)\s+(?:(?:that|to)\s+)?(.+)$')
    @authorise
    def tell(self, event, how, who, memo):
        session = ibid.databases.ibid()
        to = session.query(Identity).filter(func.lower(Identity.identity)==who.lower()).filter_by(source=event.source).first()
        if not to:
            account = session.query(Account).filter(func.lower(Account.username)==who.lower()).first()
            if account:
                for identity in account.identities:
                    if identity.source == event.source:
                        to = identity
                if not identity:
                    identity = account.identities[0]
        if not to:
            event.addresponse(u"I don't know who %s is" % who)
            return

        if permission(u'recvmemo', to.account and to.account.id or None, to.source) != 'yes':
            event.addresponse(u'Just tell %s yourself' % who)
            return

        memo = Memo(event.identity, to.id, memo, how.lower() in ('pm', 'privmsg', 'msg'))
        session.save_or_update(memo)
        session.flush()
        session.close()
        memo_cache.clear()
        log.info(u"Stored memo %s for %s (%s) from %s (%s): %s", memo.id, to.id, who, event.identity, event.sender, memo.memo)

        event.addresponse(True)

def get_memos(session, event, delivered=False):
    identities = get_identities(event, session)
    return session.query(Memo).filter_by(delivered=delivered).filter(Memo.to.in_(identities)).order_by(Memo.time.asc()).all()

class Deliver(Processor):
    feature = 'memo'

    addressed = False
    processed = True

    @handler
    def deliver(self, event):
        if event.identity in memo_cache:
            return

        session = ibid.databases.ibid()
        memos = get_memos(session, event)

        for memo in memos:
            message = 'By the way, %s on %s told me to tell you %s %s ago' % (memo.sender.identity, memo.sender.source, memo.memo, ago(datetime.now()-memo.time))
            if memo.private:
                event.addresponse({'reply': message, 'target': event.sender_id})
            else:
                event.addresponse(message)

            memo.delivered = True
            session.save_or_update(memo)
            log.info(u"Delivered memo %s to %s (%s)", memo.id, event.identity, event.sender)

        session.flush()
        session.close()
        memo_cache[event.identity] = None

class Notify(Processor):
    feature = 'memo'

    type = 'state'
    addressed = False
    processed = True

    @handler
    def state(self, event):
        if event.state not in ('joined', 'available'):
            return

        if event.identity in memo_cache:
            return

        session = ibid.databases.ibid()
        memos = get_memos(session, event)

        if len(memos) > 0:
            event.addresponse({'reply': 'You have %s messages' % len(memos), 'target': event.sender_id})
        else:
            memo_cache[event.identity] = None

        session.close()

class Messages(Processor):
    """my messages
    message <number>"""
    feature = 'memo'

    datetime_format = '%Y/%m/%d %H:%M:%S'

    @match(r'^my\s+messages$')
    def messages(self, event):
        session = ibid.databases.ibid()
        memos = get_memos(session, event, True)
        event.addresponse(', '.join(['%s: %s (%s)' % (memos.index(memo), memo.sender.identity, memo.time.strftime(self.datetime_format)) for memo in memos]))
        session.close()

    @match(r'message\s+(\d+)$')
    def message(self, event, number):
        session = ibid.databases.ibid()
        memos = get_memos(session, event, True)
        memo = memos[int(number)]
        event.addresponse(u"From %s on %s at %s: %s" % (memo.sender.identity, memo.sender.source, memo.time.strftime(self.datetime_format), memo.memo))
        session.close()


# vi: set et sta sw=4 ts=4:
