from datetime import datetime
from time import strftime

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound

import ibid
from ibid.plugins import Processor, match, handler
from ibid.models import Identity, Sighting
from ibid.plugins.identity import identify

class See(Processor):

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

        session.add(sighting)
        session.commit()
        session.close()

class Seen(Processor):

    @match('^\s*seen\s+(\S+)\s*$')
    def handler(self, event, who):
        identity = identify(event.source, who)
        if not identity:
            event.addresponse(u"I don't know who %s is" % who)
            return

        session = ibid.databases.ibid()
        try:
            sighting = session.query(Sighting).filter_by(identity_id=identity.id).first()
        except NoResultFound:
            event.addresponse(u"I haven't seen %s" % who)
            return
        finally:
            session.close()

        reply = "Saw %s at %s in " % (identity.identity, strftime('%Y/%m/%d %H:%M:%S', sighting.time.timetuple()))
        if sighting.channel:
            reply = reply + "%s saying '%s'" (sighting.channel, sighting.saying)
        else:
            reply = reply + 'private'

        event.addresponse(reply)
        return event

# vi: set et sta sw=4 ts=4:
