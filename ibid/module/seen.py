from datetime import datetime
from time import strftime

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound

import ibid
from ibid.module import Module
from ibid.decorators import *
from ibid.models import Identity, Sighting
from ibid.module.identity import identify

class Watch(Module):

    @message
    def process(self, event):
        session = ibid.databases.ibid()
        try:
            sighting = session.query(Sighting).filter_by(identity_id=event.identity).one()
        except NoResultFound:
            sighting = Sighting()
            
        sighting.channel = event.public and event.channel or None
        sighting.saying = event.public and event.message or None
        sighting.time = datetime.now()

        session.add(sighting)
        session.commit()
        session.close()

class Seen(Module):

    @addressed
    @notprocessed
    @match('^\s*seen\s+(\S+)\s*$')
    def process(self, event, who):
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

        reply = "Saw %s on %s in %s saying '%s'" % (identity.identity, strftime('%Y/%m/%d %H:%M:%S', sighting.time.timetuple()), sighting.channel, sighting.saying)

        event.addresponse(reply)
        return event

# vi: set et sta sw=4 ts=4:
