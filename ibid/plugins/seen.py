# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from datetime import datetime
import logging

from ibid.db import IbidUnicode, IbidUnicodeText, Integer, DateTime, \
                    Table, Column, ForeignKey, UniqueConstraint, \
                    relation, IntegrityError, Base, VersionedSchema
from ibid.db.models import Identity, Account
from ibid.plugins import Processor, match, handler
from ibid.utils import ago, format_date

log = logging.getLogger('plugins.seen')

features = {'seen': {
    'description': u'Records when people were last seen.',
    'categories': ('remember', 'lookup',),
}}

class Sighting(Base):
    __table__ = Table('seen', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('identity_id', Integer, ForeignKey('identities.id'), nullable=False,
           index=True),
    Column('type', IbidUnicode(8), nullable=False, index=True),
    Column('channel', IbidUnicode(32)),
    Column('value', IbidUnicodeText),
    Column('time', DateTime, nullable=False),
    Column('count', Integer, nullable=False),
    UniqueConstraint('identity_id', 'type'),
    useexisting=True)

    class SightingSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.identity_id)
            self.add_index(self.table.c.type)
        def upgrade_2_to_3(self):
            self.drop_index(self.table.c.type)
            self.alter_column(Column('type', IbidUnicode(8), nullable=False,
                                     index=True), force_rebuild=True)
            self.alter_column(Column('channel', IbidUnicode(32)),
                              force_rebuild=True)
            self.alter_column(Column('value', IbidUnicodeText),
                              force_rebuild=True)
            self.add_index(self.table.c.type)

    __table__.versioned_schema = SightingSchema(__table__, 3)

    identity = relation('Identity')

    def __init__(self, identity_id=None, type='message', channel=None,
                 value=None):
        self.identity_id = identity_id
        self.type = type
        self.channel = channel
        self.value = value
        self.time = datetime.utcnow()
        self.count = 0

    def __repr__(self):
        return u'<Sighting %s %s in %s at %s: %s>' % (
               self.type, self.identity_id, self.channel, self.time, self.value)

class See(Processor):
    feature = ('seen',)

    priority = 1500
    event_types = (u'message', u'state')
    addressed = False
    processed = True

    @handler
    def see(self, event):
        sighting = event.session.query(Sighting) \
                .filter_by(identity_id=event.identity, type=event.type).first()
        if not sighting:
            sighting = Sighting(event.identity, event.type)

        if 'channel' in event:
            sighting.channel = 'public' in event and event.public and event.channel or None
        if event.type == 'message':
            sighting.value = event.public and event.message['raw'] or None
        elif event.type == 'state':
            sighting.value = event.state
        sighting.time = event.time
        sighting.count = sighting.count + 1

        event.session.save_or_update(sighting)
        try:
            event.session.commit()
        except IntegrityError:
            event.session.rollback()
            event.session.close()
            del event['session']
            log.debug(u'Race encountered updating seen for %s on %s',
                    event.sender['id'], event.source)

class Seen(Processor):
    usage = u'seen <who>'
    feature = ('seen',)

    @match(r'^(?:have\s+you\s+)?seen\s+(\S+)(?:\s+on\s+(\S+))?$')
    def handler(self, event, who, source):

        account = None
        identity = event.session.query(Identity) \
                .filter_by(source=(source or event.source), identity=who) \
                .first()
        if identity and identity.account and not source:
            account = identity.account

        if not identity and not source:
            account = event.session.query(Account).filter_by(username=who) \
                    .first()

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
            delta = event.time - sighting.time
            reply = u'%s was last seen %s ago in %s on %s [%s]' %(
                    who, ago(delta), sighting.channel or 'private',
                    sighting.identity.source, format_date(sighting.time))

        if len(states) > 0:
            sighting = states[0]
            if reply:
                reply += u', and'
            else:
                reply = who
            reply += u' has been %s on %s since %s' % (
                    sighting.value, sighting.identity.source,
                    format_date(sighting.time))

        event.addresponse(reply)

# vi: set et sta sw=4 ts=4:
