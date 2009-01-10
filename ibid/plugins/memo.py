from datetime import datetime
from time import strftime

from sqlalchemy import Column, Integer, Unicode, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, handler, match
from ibid.models import Identity, Account, Memo
from ibid.utils import ago

help = {'memo': 'Keeps messages for people.'}

memo_cache = {}

class Tell(Processor):
    """(tell|pm|privmsg|msg) <person> <message>"""
    feature = 'memo'

    @match(r'^(?:please\s+)?(tell|pm|privmsg|msg)\s+(\S+)\s+(?:(?:that|to)\s+)?(.+)$')
    def tell(self, event, how, who, memo):
        session = ibid.databases.ibid()
        to = session.query(Identity).filter(func.lower(Identity.identity)==who.lower()).filter_by(source=event.source).first()
        if not to:
            account = session.query(Account).filter(func.lower(Account.username)==who.lower()).first()
            for identity in account.identities:
                if identity.source == event.source:
                    to = identity
            if not identity:
                identity = account.identities[0]
        if not to:
            event.addresponse(u"I don't know who %s is" % who)
            return

        memo = Memo(event.identity, to.id, memo, how.lower() in ('pm', 'privmsg'))
        session.save_or_update(memo)
        session.commit()
        session.close()
        memo_cache.clear()

        event.addresponse(True)

def get_memos(session, event, delivered=False):
    if event.account:
        account = session.query(Account).get(event.account)
        identities = [identity.id for identity in account.identities]
    else:
        identities = (event.identity,)
    return session.query(Memo).filter_by(delivered=delivered).filter(Memo.to.in_(identities)).order_by(Memo.time.asc()).all()

class Deliver(Processor):
    feature = 'memo'

    addressed = False
    processed = True

    @handler
    def deliver(self, event):
        print memo_cache
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

        session.commit()
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

        session = ibid.databases.ibid()
        memos = get_memos(session, event)

        if len(memos) > 0:
                event.addresponse({'reply': 'You have %s messages' % len(memos), 'target': event.sender_id})

        session.close()

class Messages(Processor):
    """my messages
    message <number>"""
    feature = 'memo'

    @match(r'^my\s+messages$')
    def messages(self, event):
        session = ibid.databases.ibid()
        memos = get_memos(session, event, True)
        event.addresponse(', '.join(['%s: %s (%s)' % (memos.index(memo), memo.sender.identity, strftime('%Y/%m/%d %H:%M:%S', memo.time.timetuple())) for memo in memos]))
        session.close()

    @match(r'message\s+(\d+)$')
    def message(self, event, number):
        session = ibid.databases.ibid()
        memos = get_memos(session, event, True)
        memo = memos[int(number)]
        event.addresponse(u"From %s on %s at %s: %s" % (memo.sender.identity, memo.sender.source, strftime('%Y/%m/%d %H:%M:%S', memo.time.timetuple()), memo.memo))
        session.close()


# vi: set et sta sw=4 ts=4:
