from datetime import datetime
from random import choice
from time import localtime, strftime
import re
import logging

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey, UnicodeText, UniqueConstraint
from sqlalchemy.orm import relation, mapper, eagerload
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

import ibid
from ibid.plugins import Processor, match, handler, authorise, auth_responses
from ibid.plugins.identity import get_identities
from ibid.models import Account

help = {'factoids': u'Factoids are arbitrary pieces of information stored by a key.'}

Base = declarative_base()
log = logging.getLogger('plugins.factoid')

class Factoid(Base):
    __tablename__ = 'factoids'

    id = Column(Integer, primary_key=True)
    names = relation('FactoidName', cascade='all,delete')
    values = relation('FactoidValue', cascade='all,delete')

    def __repr__(self):
        return u"<Factoid %s = %s>" % (', '.join([name.name for name in self.names]), ', '.join([value.value for value in self.values]))

class FactoidName(Base):
    __tablename__ = 'factoid_names'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(128), nullable=False, unique=True)
    factoid_id = Column(Integer, ForeignKey(Factoid.id), nullable=False)
    factoid = relation(Factoid)
    identity = Column(Integer)
    time = Column(DateTime, nullable=False)

    def __init__(self, name, identity, factoid_id=None):
        self.name = name
        self.factoid_id = factoid_id
        self.identity = identity
        self.time = datetime.now()

    def __repr__(self):
        return u'<FactoidName %s %s>' % (self.name, self.factoid_id)

class FactoidValue(Base):
    __tablename__ = 'factoid_values'

    id = Column(Integer, primary_key=True)
    value = Column(UnicodeText, nullable=False)
    factoid_id = Column(Integer, ForeignKey(Factoid.id), nullable=False)
    factoid = relation(Factoid)
    identity = Column(Integer)
    time = Column(DateTime, nullable=False)

    def __init__(self, value, identity, factoid_id=None):
        self.value = value
        self.factoid_id = factoid_id
        self.identity = identity
        self.time = datetime.now()

    def __repr__(self):
        return u'<FactoidValue %s %s>' % (self.factoid_id, self.value)

action_re = re.compile(r'^\s*<action>\s*')
reply_re = re.compile(r'^\s*<reply>\s*')
verbs = ('is', 'are', 'has', 'have', 'was', 'were', 'do', 'does', 'can', 'should', 'would')

def escape_name(name):
    return name.replace('%', '\\%').replace('_', '\\_').replace('$arg', '_%')

def get_factoid(session, name, number, pattern, all=False):
    factoid = None
    query = session.query(Factoid).add_entity(FactoidName).add_entity(FactoidValue).join('names').filter(":fact LIKE name ESCAPE '\\'").params(fact=name).join('values')
    if pattern:
        query = query.filter(FactoidValue.value.op('REGEXP')(pattern))
    if number:
        try:
            factoid = query.order_by(FactoidValue.id)[int(number)]
        except IndexError:
            return
    if all:
        return factoid and [factoid] or query.all()
    else:
        return factoid or query.order_by(func.random()).first()

class Utils(Processor):
    """literal <name> [starting at <number>]"""
    feature = 'factoids'

    @match(r'^literal\s+(.+?)(?:\s+start(?:ing)?\s+(?:from\s+)?(\d+))?$')
    def literal(self, event, name, start):
        start = start and int(start) or 0
        session = ibid.databases.ibid()
        factoid = session.query(Factoid).options(eagerload('values')).join('names').filter(func.lower(FactoidName.name)==escape_name(name).lower()).order_by(FactoidValue.id).first()
        if factoid:
            event.addresponse(', '.join(['%s: %s' % (factoid.values.index(value), value.value) for value in factoid.values[start:]]))

        session.close()

class Forget(Processor):
    """forget <name>"""
    feature = 'factoids'

    permission = u'factoid'
    permissions = (u'factoidadmin',)

    @match(r'^forget\s+(.+?)(?:\s+#(\d+)|\s+/(.+?)/)?$')
    @authorise
    def forget(self, event, name, number, pattern):
        session = ibid.databases.ibid()
        factoids = get_factoid(session, name, number, pattern, True)
        if factoids:
            factoidadmin = auth_responses(event, u'factoidadmin')
            identities = get_identities(event, session)
            factoid = factoids[0][0]

            if (number or pattern):
                if len(factoids) > 1:
                    event.addresponse(u"Pattern matches multiple factoids, please be more specific")
                    return

                if factoids[0][2].identity not in identities and not factoidadmin:
                    return

                if len(factoid.values) == 1:
                    if len(filter(lambda x: x.identity not in identities, factoid.names)) > 0 and not factoidadmin:
                        return
                    log.info(u"Deleting factoid %s (%s) by %s/%s (%s)", factoid.id, name, event.account, event.identity, event.sender)
                    session.delete(factoid)
                else:
                    log.info(u"Deleting value %s of factoid %s (%s) by %s/%s (%s)", factoids[0][2].id, factoid.id, factoids[0][2].value, event.account, event.identity, event.sender)
                    session.delete(factoids[0][2])

            else:
                if factoids[0][1].identity not in identities and not factoidadmin:
                    return

                if len(factoid.names) == 1:
                    if len(filter(lambda x: x.identity not in identities, factoid.values)) > 0 and not factoidadmin:
                        return
                    log.info(u"Deleting factoid %s (%s) by %s/%s (%s)", factoid.id, name, event.account, event.identity, event.sender)
                    session.delete(factoid)
                else:
                    log.info(u"Deleting name %s of factoid %s (%s) by %s/%s (%s)", factoids[0][1].id, factoid.id, factoids[0][1].name, event.account, event.identity, event.sender)
                    session.delete(factoids[0][1])

            session.flush()
            session.close()
            event.addresponse(True)
        else:
            event.addresponse(u"I didn't know about %s anyway" % name)

    @match(r'^(.+)\s+is\s+the\s+same\s+as\s+(.+)$')
    @authorise
    def alias(self, event, target, source):

        session = ibid.databases.ibid()
        factoid = session.query(Factoid).join('names').filter(func.lower(FactoidName.name)==escape_name(source).lower()).first()
        if factoid:
            name = FactoidName(escape_name(unicode(target)), event.identity)
            factoid.names.append(name)
            session.save_or_update(factoid)
            session.flush()
            session.close()
            event.addresponse(True)
            log.info(u"Added name '%s' to factoid %s by %s/%s (%s)", name.name, factoid.id, event.account, event.identity, event.sender)
        else:
            event.addresponse(u"I don't know about %s" % name)

class Get(Processor):
    """<factoid> [( #<number> | /<pattern>/ )]"""
    feature = 'factoids'

    verbs = verbs
    priority = 900
    interrogatives = ('what', 'wtf', 'where', 'when', 'who', "what's", "who's")
    date_format = '%Y/%m/%d'
    time_format = '%H:%M:%S'

    def setup(self):
        self.get.im_func.pattern = re.compile(r'^(?:(?:%s)\s+(?:(%s)\s+)?)?(.+?)(?:\s+#(\d+))?(?:\s+/(.+?)/)?$' % ('|'.join(self.interrogatives), '|'.join(self.verbs)), re.I)

    @handler
    def get(self, event, verb, name, number, pattern):
        session = ibid.databases.ibid()
        factoid = get_factoid(session, name, number, pattern)
        session.close()

        if factoid:
            (factoid, fname, fvalue) = factoid
            reply = fvalue.value
            pattern = re.escape(fname.name).replace(r'\_\%', '(.*)').replace('\\\\\\%', '%').replace('\\\\\\_', '_')

            position = 1
            for capture in re.match(pattern, name, re.I).groups():
                if capture.startswith('$arg'):
                    return
                reply = reply.replace('$%s' % position, capture)
                position = position + 1

            reply = reply.replace('$who', event.who)
            reply = reply.replace('$channel', event.channel)
            now = localtime()
            reply = reply.replace('$year', str(now[0]))
            reply = reply.replace('$month', str(now[1]))
            reply = reply.replace('$day', str(now[2]))
            reply = reply.replace('$hour', str(now[3]))
            reply = reply.replace('$minute', str(now[4]))
            reply = reply.replace('$second', str(now[5]))
            reply = reply.replace('$date', strftime(self.date_format, now))
            reply = reply.replace('$time', strftime(self.time_format, now))
            reply = reply.replace('$dow', strftime('%A', now))

            (reply, count) = action_re.subn('', reply)
            if count:
                event.addresponse({'action': True, 'reply': reply})
            else:
                (reply, count) = reply_re.subn('', reply)
                if count:
                    event.addresponse({'reply': reply})
                else:
                    reply = '%s %s' % (fname.name.replace('_%', '$arg').replace('\\%', '%').replace('\\_', '_'), reply)
                    event.addresponse(reply)

class Set(Processor):
    """<name> (<verb>|=<verb>=) <value>
    <name> is the same as <name>"""
    feature = 'factoids'

    verbs = verbs
    priority = 910
    permission = u'factoid'
    
    def setup(self):
        self.set_factoid.im_func.pattern = re.compile(r'^(no[,.: ]\s*)?(.+?)\s+(?:=(\S+)=)?(?(3)|(%s))(\s+also)?\s+(.+?)$' % '|'.join(self.verbs), re.I)

    @handler
    @authorise
    def set_factoid(self, event, correction, name, verb1, verb2, addition, value):
        verb = verb1 and verb1 or verb2

        session = ibid.databases.ibid()
        factoid = session.query(Factoid).join('names').filter(func.lower(FactoidName.name)==escape_name(name).lower()).first()
        if factoid:
            if correction:
                identities = get_identities(event, session)
                if not auth_responses(event, u'factoidadmin') and len(filter(lambda x: x.identity not in identities, factoid.values)) > 0:
                    return
                for fvalue in factoid.values:
                    session.delete(fvalue)
                session.flush()
            elif not addition:
                event.addresponse(u"I already know stuff about %s" % name)
                return
        else:
            factoid = Factoid()
            fname = FactoidName(escape_name(unicode(name)), event.identity)
            factoid.names.append(fname)
            log.info(u"Created factoid %s with name '%s' by %s", factoid.id, fname.name, event.identity)

        if not reply_re.match(value) and not action_re.match(value):
            value = '%s %s' % (verb, value)
        fvalue = FactoidValue(unicode(value), event.identity)
        factoid.values.append(fvalue)
        log.info(u"Added value '%s' to factoid %s by %s/%s (%s)", fvalue.value, factoid.id, event.account, event.identity, event.sender)
        session.save_or_update(factoid)
        session.flush()
        session.close()
        event.addresponse(True)

# vi: set et sta sw=4 ts=4:
