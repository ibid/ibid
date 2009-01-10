from datetime import datetime

from sqlalchemy import Column, Integer, Unicode, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, handler, match
from ibid.models import Identity, Account, Memo
from ibid.utils import ago

class Tell(Processor):

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
        session.add(memo)
        session.commit()
        session.close()

        event.addresponse(True)

class Deliver(Processor):

    addressed = False
    processed = True

    @handler
    def deliver(self, event):
        session = ibid.databases.ibid()
        if event.account:
            account = session.query(Account).get(event.account)
            identities = [identity.id for identity in account.identities]
        else:
            identities = (event.identity,)
        memos = session.query(Memo).filter_by(delivered=False).filter(Memo.to.in_(identities)).all()
        for memo in memos:
            message = 'By the way, %s told me to tell you %s %s ago' % (memo.sender.identity, memo.memo, ago(datetime.now()-memo.time))
            if memo.private:
                event.addresponse({'reply': message, 'target': event.sender_id})
            else:
                event.addresponse(message)

            memo.delivered = True
            session.add(memo)

        session.commit()
        session.close()

# vi: set et sta sw=4 ts=4:
