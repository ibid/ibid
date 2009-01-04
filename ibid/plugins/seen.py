from datetime import datetime
from time import strftime

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match, handler
from ibid.models import Identity, Sighting, Account
from ibid.plugins.identity import identify
from ibid.utils import ago

class See(Processor):

    priority = 1500

    def process(self, event):
        if event.type != 'message' and event.type != 'state':
            return

        session = ibid.databases.ibid()
        sighting = session.query(Sighting).filter_by(identity_id=event.identity).filter_by(type=event.type).first()
        if not sighting:
            sighting = Sighting()
            sighting.identity_id = event.identity
            sighting.type = event.type

        if 'channel' in event:
            sighting.channel = 'public' in event and event.public and event.channel or None
        if event.type == 'message':
            sighting.value = event.public and event.message or None
        elif event.type == 'state':
            sighting.value = event.state
        sighting.time = datetime.now()
        sighting.count = sighting.count + 1

        session.add(sighting)
        session.commit()
        session.close()

class Seen(Processor):

    @match(r'^(?:have\s+you\s+)?seen\s+(\S+)(?:\s+on\s+(\S+))?$')
    def handler(self, event, who, source):

        session = ibid.databases.ibid()
        account = None
        identity = session.query(Identity).filter(func.lower(Identity.source)==(source and source or event.source).lower()).filter(func.lower(Identity.identity)==who.lower()).first()
        if identity and identity.account and not source:
            account = identity.account

        if not identity and not source:
            account = session.query(Account).filter_by(username=who).first()

        if not identity and not account:
            event.addresponse(u"I don't know who %s is" % who)
            return

        messages = []
        states = []
        if account:
            for identity in account.identities:
                for sighting in session.query(Sighting).filter_by(identity_id=identity.id).all():
                    if sighting.type == 'message':
                        messages.append(sighting)
                    else:
                        states.append(sighting)
        else:
            for sighting in session.query(Sighting).filter_by(identity_id=identity.id).all():
                if sighting.type == 'message':
                    messages.append(sighting)
                else:
                    states.append(sighting)

        if len(messages) == 0 and len(states) == 0:
            event.addresponse(u"I haven't seen %s" % who)
            return

        messages.sort(key=lambda x: x.time, reverse=True)
        states.sort(key=lambda x: x.time, reverse=True)

        reply = ''
        if len(messages) > 0:
            sighting = messages[0]
            delta = datetime.now() - sighting.time
            reply = u"%s was last seen %s ago in %s on %s" % (who, ago(delta), sighting.channel or 'private', sighting.identity.source)
            reply = u'%s [%s]' % (reply, strftime('%Y/%m/%d %H:%M:%S', sighting.time.timetuple()))

        if len(states) > 0:
            sighting = states[0]
            if reply:
                reply = reply + u', and'
            else:
                reply = who
            reply = reply + u" has been %s on %s since %s" % (sighting.value, sighting.identity.source, strftime('%Y/%m/%d %H:%M:%S', sighting.time.timetuple()))

        event.addresponse(reply)
        session.close()
        return event

# vi: set et sta sw=4 ts=4:
