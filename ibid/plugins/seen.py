from datetime import datetime
import logging

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey, UnicodeText, UniqueConstraint, Table
from sqlalchemy.orm import relation
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.models import Base, VersionedSchema, Identity, Account
from ibid.utils import ago

log = logging.getLogger('plugins.seen')

help = {'seen': u'Records when people were last seen.'}

class Sighting(Base):
    __table__ = Table('seen', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('identity_id', Integer, ForeignKey('identities.id'), nullable=False),
    Column('type', Unicode(8), nullable=False),
    Column('channel', Unicode(32)),
    Column('value', UnicodeText),
    Column('time', DateTime, nullable=False, default=func.current_timestamp()),
    Column('count', Integer, nullable=False),
    UniqueConstraint('identity_id', 'type'),
    useexisting=True)

    __table__.versioned_schema = VersionedSchema(__table__, 1)

    identity = relation('Identity')

    def __init__(self, identity_id=None, type='message', channel=None, value=None):
        self.identity_id = identity_id
        self.type = type
        self.channel = channel
        self.value = value
        self.count = 0

    def __repr__(self):
        return u'<Sighting %s %s in %s at %s: %s>' % (self.type, self.identity_id, self.channel, self.time, self.value)

class See(Processor):
    feature = 'seen'

    priority = 1500

    def process(self, event):
        if event.type != 'message' and event.type != 'state':
            return

        sighting = event.session.query(Sighting) \
                .filter_by(identity_id=event.identity) \
                .filter_by(type=event.type).first()
        if not sighting:
            sighting = Sighting(event.identity, event.type)

        if 'channel' in event:
            sighting.channel = 'public' in event and event.public and event.channel or None
        if event.type == 'message':
            sighting.value = event.public and event.message['raw'] or None
        elif event.type == 'state':
            sighting.value = event.state
        sighting.time = datetime.now()
        sighting.count = sighting.count + 1

        event.session.save_or_update(sighting)

class Seen(Processor):
    u"""seen <who>"""
    feature = 'seen'

    datetime_format = Option('datetime_format', 'Format string for timestamps', '%Y/%m/%d %H:%M:%S')

    @match(r'^(?:have\s+you\s+)?seen\s+(\S+)(?:\s+on\s+(\S+))?$')
    def handler(self, event, who, source):

        account = None
        identity = event.session.query(Identity) \
                .filter(func.lower(Identity.source) == (source and source or event.source).lower()) \
                .filter(func.lower(Identity.identity) == who.lower()).first()
        if identity and identity.account and not source:
            account = identity.account

        if not identity and not source:
            account = event.session.query(Account).filter_by(username=who).first()

        if not identity and not account:
            event.addresponse(u"I don't know who %s is", who)
            return

        messages = []
        states = []
        if account:
            for identity in account.identities:
                for sighting in event.session.query(Sighting) \
                        .filter_by(identity_id=identity.id).all():
                    if sighting.type == 'message':
                        messages.append(sighting)
                    else:
                        states.append(sighting)
        else:
            for sighting in event.session.query(Sighting) \
                    .filter_by(identity_id=identity.id).all():
                if sighting.type == 'message':
                    messages.append(sighting)
                else:
                    states.append(sighting)

        if len(messages) == 0 and len(states) == 0:
            event.addresponse(u"I haven't seen %s", who)
            return

        messages.sort(key=lambda x: x.time, reverse=True)
        states.sort(key=lambda x: x.time, reverse=True)

        reply = u''
        if len(messages) > 0:
            sighting = messages[0]
            delta = datetime.now() - sighting.time
            reply = u"%s was last seen %s ago in %s on %s" % (who, ago(delta), sighting.channel or 'private', sighting.identity.source)
            reply += u' [%s]' % sighting.time.strftime(self.datetime_format)

        if len(states) > 0:
            sighting = states[0]
            if reply:
                reply += u', and'
            else:
                reply = who
            reply += u" has been %s on %s since %s" % (sighting.value, sighting.identity.source, sighting.time.strftime(self.datetime_format))

        event.addresponse(reply)

# vi: set et sta sw=4 ts=4:
