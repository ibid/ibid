from datetime import datetime
from time import strftime

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound

import ibid
from ibid.plugins import Processor, match, handler
from ibid.models import Identity, Sighting, Account
from ibid.plugins.identity import identify

class See(Processor):

    priority = 1500

    def process(self, event):
        if event.type != 'message' and event.type != 'state':
            return

        session = ibid.databases.ibid()
        try:
            sighting = session.query(Sighting).filter_by(identity_id=event.identity).filter_by(type=event.type).one()
        except NoResultFound:
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

    @match('^(?:have\s+you\s+)?seen\s+(\S+)(?:\s+on\s+(\S+))?$')
    def handler(self, event, who, source):

        session = ibid.databases.ibid()
        account = None
        identity = None
        try:
            identity = session.query(Identity).filter_by(source=source or event.source).filter_by(identity=who).one()
            if identity.account and not source:
                account = identity.account

        except NoResultFound:
            if not source:
                try:
                    account = session.query(Account).filter_by(username=who).one()
                except NoResultFound:
                    pass

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

        if len(messages) > 0:
            sighting = messages[0]
            reply = u"I've seen %s %s times on %s, and last at %s in %s" % (who, sighting.count, sighting.identity.source, strftime('%Y/%m/%d %H:%M:%S', sighting.time.timetuple()), sighting.channel or 'private')
            if sighting.value:
                reply = reply + " saying '%s'" % sighting.value
            event.addresponse(reply)

        if len(states) > 0:
            sighting = states[0]
            event.addresponse(u"%s's state on %s has been %s since %s and has changed %s times" % (who, sighting.identity.source, sighting.value, strftime('%Y/%m/%d %H:%M:%S', sighting.time.timetuple()), sighting.count))

        session.close()
        return event

# vi: set et sta sw=4 ts=4:
