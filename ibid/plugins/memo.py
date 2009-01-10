from datetime import datetime

from sqlalchemy import Column, Integer, Unicode, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, handler, match
from ibid.models import Identity
from ibid.utils import ago

Base = declarative_base()

class Memo(Base):
    __tablename__ = 'memos'

    id = Column(Integer, primary_key=True)
    frm = Column(Integer)
    to = Column(Integer)
    memo = Column(Unicode)
    private = Column(Boolean)
    delivered = Column(Boolean)
    time = Column(DateTime)

    def __init__(self, frm, to, memo, private=False):
        self.frm = frm
        self.to = to
        self.memo = memo
        self.private = private
        self.delivered = False
        self.time = datetime.now()

class Tell(Processor):

    @match(r'^(?:please\s+)?(tell|pm|privmsg|msg)\s+(\S+)\s+(?:(?:that|to)\s+)?(.+)$')
    def tell(self, event, how, who, memo):
        session = ibid.databases.ibid()
        to = session.query(Identity).filter(func.lower(Identity.identity)==who.lower()).filter_by(source=event.source).first()
        if not to:
            to = session.query(Account).filter(func.lower(Account.username)==who.lower()).first()
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
        memos = session.query(Memo).filter_by(delivered=False).filter_by(to=event.identity).all()
        for memo in memos:
            message = '%s told me to tell you %s %s ago' % (memo.frm, memo.memo, ago(datetime.now()-memo.time))
            if memo.private:
                event.addresponse({'reply': message, 'target': event.sender_id})
            else:
                event.addresponse(message)

            memo.delivered = True
            session.add(memo)

        session.commit()
        session.close()

# vi: set et sta sw=4 ts=4:
