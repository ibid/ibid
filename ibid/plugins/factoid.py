from time import localtime, strftime, time
import re
import logging

from sqlalchemy import Column, Integer, Unicode, DateTime, ForeignKey, UnicodeText, Table, or_
from sqlalchemy.orm import relation, eagerload
from sqlalchemy.sql import func

from ibid.plugins import Processor, match, handler, authorise, auth_responses, RPC
from ibid.config import Option, IntOption
from ibid.plugins.identity import get_identities
from ibid.models import Base, VersionedSchema

help = {'factoids': u'Factoids are arbitrary pieces of information stored by a key. '
                    u'Factoids beginning with a command such as "<action>" or "<reply>" will supress the "name verb value" output. '
                    u"Search and replace functions won't use real regexs unless appended with the 'r' flag."}

log = logging.getLogger('plugins.factoid')

class FactoidName(Base):
    __table__ = Table('factoid_names', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Unicode(128), nullable=False),
    Column('factoid_id', Integer, ForeignKey('factoids.id'), nullable=False),
    Column('identity_id', Integer, ForeignKey('identities.id')),
    Column('time', DateTime, nullable=False, default=func.current_timestamp()),
    Column('factpack', Integer, ForeignKey('factpacks.id')),
    useexisting=True)

    class FactoidNameSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_column(Column('factpack', Integer, ForeignKey('factpacks.id')))

    __table__.versioned_schema = FactoidNameSchema(__table__, 2)

    def __init__(self, name, identity_id, factoid_id=None, factpack=None):
        self.name = name
        self.factoid_id = factoid_id
        self.identity_id = identity_id
        self.factpack = factpack

    def __repr__(self):
        return u'<FactoidName %s %s>' % (self.name, self.factoid_id)

class FactoidValue(Base):
    __table__ = Table('factoid_values', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('value', UnicodeText, nullable=False),
    Column('factoid_id', Integer, ForeignKey('factoids.id'), nullable=False),
    Column('identity_id', Integer, ForeignKey('identities.id')),
    Column('time', DateTime, nullable=False, default=func.current_timestamp()),
    Column('factpack', Integer, ForeignKey('factpacks.id')),
    useexisting=True)

    class FactoidValueSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_column(Column('factpack', Integer, ForeignKey('factpacks.id')))

    __table__.versioned_schema = FactoidValueSchema(__table__, 2)

    def __init__(self, value, identity_id, factoid_id=None, factpack=None):
        self.value = value
        self.factoid_id = factoid_id
        self.identity_id = identity_id
        self.factpack = factpack

    def __repr__(self):
        return u'<FactoidValue %s %s>' % (self.factoid_id, self.value)

class Factoid(Base):
    __table__ = Table('factoids', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('time', DateTime, nullable=False, default=func.current_timestamp()),
    Column('factpack', Integer, ForeignKey('factpacks.id')),
    useexisting=True)

    __table__.versioned_schema = VersionedSchema(__table__, 1)

    names = relation(FactoidName, cascade='all,delete', backref='factoid')
    values = relation(FactoidValue, cascade='all,delete', backref='factoid')

    class FactoidSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_column(Column('factpack', Integer, ForeignKey('factpacks.id')))

    __table__.versioned_schema = FactoidSchema(__table__, 2)

    def __init__(self, factpack=None):
        self.factpack = factpack

    def __repr__(self):
        return u"<Factoid %s = %s>" % (', '.join([name.name for name in self.names]), ', '.join([value.value for value in self.values]))

class Factpack(Base):
    __table__ = Table('factpacks', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Unicode(64), nullable=False, unique=True),
    useexisting=True)

    __table__.versioned_schema = VersionedSchema(__table__, 1)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return u'<Factpack %s>' % (self.name,)

action_re = re.compile(r'^\s*<action>\s*')
reply_re = re.compile(r'^\s*<reply>\s*')
escape_like_re = re.compile(r'([%_\\])')
verbs = ('is', 'are', 'has', 'have', 'was', 'were', 'do', 'does', 'can', 'should', 'would')

def escape_name(name):
    return name.replace('%', '\\%').replace('_', '\\_').replace('$arg', '_%')

def unescape_name(name):
    return name.replace('_%', '$arg').replace('\\%', '%').replace('\\_', '_')

def get_factoid(session, name, number, pattern, is_regex, all=False, literal=False):
    """session: SQLAlchemy session
    name: Factoid name (can contain arguments unless literal query)
    number: Return factoid[number] (or factoid[number:] for literal queries)
    pattern: Return factoids matching this pattern (cannot be used in conjuction with number)
    is_regex: Pattern is a real regex
    all: Return a random factoid from the set if False
    literal: Match factoid name literally (implies all)
    """
    factoid = None
    # Reversed LIKE because factoid name contains SQL wildcards if factoid supports arguments
    query = session.query(Factoid)\
            .add_entity(FactoidName).join(Factoid.names)\
            .add_entity(FactoidValue).join(Factoid.values)
    if literal:
        query = query.filter(func.lower(FactoidName.name)==escape_name(name).lower())
    else:
        query = query.filter(":fact LIKE name ESCAPE :escape").params(fact=name, escape='\\')
    if pattern:
        if is_regex:
            query = query.filter(FactoidValue.value.op('REGEXP')(pattern))
        else:
            pattern = "%%%s%%" % escape_like_re.sub(r'\\\1', pattern)
            # http://www.sqlalchemy.org/trac/ticket/1400: We can't use .like() in MySQL
            query = query.filter('value LIKE :pattern ESCAPE :escape').params(pattern=pattern, escape='\\')
    if number:
        try:
            if literal:
                return query.order_by(FactoidValue.id)[int(number):]
            else:
                factoid = query.order_by(FactoidValue.id)[int(number)]
        except IndexError:
            return
    if all or literal:
        return factoid and [factoid] or query.all()
    else:
        return factoid or query.order_by(func.random()).first()

class Utils(Processor):
    u"""literal <name> [( #<from number> | /<pattern>/[r] )]"""
    feature = 'factoids'

    @match(r'^literal\s+(.+?)(?:\s+#(\d+)|\s+(?:/(.+?)/(r?)))?$')
    def literal(self, event, name, number, pattern, is_regex):
        factoids = get_factoid(event.session, name, number, pattern, is_regex, literal=True)
        number = number and int(number) or 0
        if factoids:
            event.addresponse(u', '.join(u'%i: %s'
                % (index + number, value.value) for index, (factoid, name, value) in enumerate(factoids)))

class Forget(Processor):
    u"""forget <name> [( #<number> | /<pattern>/[r] )]
    <name> is the same as <other name>"""
    feature = 'factoids'

    permission = u'factoid'
    permissions = (u'factoidadmin',)

    @match(r'^forget\s+(.+?)(?:\s+#(\d+)|\s+(?:/(.+?)/(r?)))?$')
    @authorise
    def forget(self, event, name, number, pattern, is_regex):
        factoids = get_factoid(event.session, name, number, pattern, is_regex, all=True)
        if factoids:
            factoidadmin = auth_responses(event, u'factoidadmin')
            identities = get_identities(event)
            factoid = event.session.query(Factoid).get(factoids[0][0].id)

            if (number or pattern):
                if len(factoids) > 1:
                    event.addresponse(u'Pattern matches multiple factoids, please be more specific')
                    return

                if factoids[0][2].identity_id not in identities and not factoidadmin:
                    return

                if event.session.query(FactoidValue).filter_by(factoid_id=factoid.id).count() == 1:
                    if len(filter(lambda x: x.identity_id not in identities, factoid.names)) > 0 and not factoidadmin:
                        return
                    id = factoid.id
                    event.session.delete(factoid)
                    event.session.commit()
                    log.info(u"Deleted factoid %s (%s) by %s/%s (%s)",
                            id, name, event.account, event.identity, event.sender['connection'])
                else:
                    id = factoids[0][2].id
                    event.session.delete(factoids[0][2])
                    event.session.commit()
                    log.info(u"Deleted value %s (%s) of factoid %s (%s) by %s/%s (%s)",
                            id, factoids[0][2].value, factoid.id, name,
                            event.account, event.identity, event.sender['connection'])

            else:
                if factoids[0][1].identity_id not in identities and not factoidadmin:
                    return

                if event.session.query(FactoidName).filter_by(factoid_id=factoid.id).count() == 1:
                    if len(filter(lambda x: x.identity_id not in identities, factoid.values)) > 0 and not factoidadmin:
                        return
                    id = factoid.id
                    event.session.delete(factoid)
                    event.session.commit()
                    log.info(u"Deleted factoid %s (%s) by %s/%s (%s)",
                            id, name, event.account, event.identity,
                            event.sender['connection'])
                else:
                    id = factoids[0][1].id
                    event.session.delete(factoids[0][1])
                    event.session.commit()
                    log.info(u"Deleted name %s (%s) of factoid %s (%s) by %s/%s (%s)",
                            id, factoids[0][1].name, factoid.id, factoids[0][0].names[0].name,
                            event.account, event.identity, event.sender['connection'])

            event.addresponse(True)
        else:
            event.addresponse(u"I didn't know about %s anyway", name)

    @match(r'^(.+)\s+is\s+the\s+same\s+as\s+(.+)$')
    @authorise
    def alias(self, event, target, source):

        if target.lower() == source.lower():
            event.addresponse(u"That makes no sense, they *are* the same")
            return

        factoid = event.session.query(Factoid).join(Factoid.names)\
                .filter(func.lower(FactoidName.name)==escape_name(source).lower()).first()
        if factoid:
            name = FactoidName(escape_name(unicode(target)), event.identity)
            factoid.names.append(name)
            event.session.save_or_update(factoid)
            event.session.commit()
            event.addresponse(True)
            log.info(u"Added name '%s' to factoid %s (%s) by %s/%s (%s)",
                    name.name, factoid.id, factoid.names[0].name,
                    event.account, event.identity, event.sender['connection'])
        else:
            event.addresponse(u"I don't know about %s", source)

class Search(Processor):
    u"""search [for] [<limit>] [(facts|values) [containing]] (<pattern>|/<pattern>/[r]) [from <start>]"""
    feature = 'factoids'

    limit = IntOption('search_limit', u'Maximum number of results to return', 30)
    default = IntOption('search_default', u'Default number of results to return', 10)

    regex_re = re.compile(r'^/(.*)/(r?)$')

    @match(r'^search\s+(?:for\s+)?(?:(\d+)\s+)?(?:(facts?|values?)\s+)?(?:containing\s+)?(.+?)(?:\s+from\s+)?(\d+)?$')
    def search(self, event, limit, search_type, pattern, start):
        limit = limit and min(int(limit), self.limit) or self.default
        start = start and int(start) or 0

        search_type = search_type and search_type.lower() or u""

        m = self.regex_re.match(pattern)
        is_regex = False
        if m:
            pattern = m.group(1)
            is_regex = bool(m.group(2))

        query = event.session.query(Factoid)\
                .join(Factoid.names).add_entity(FactoidName)\
                .join(Factoid.values)

        if search_type.startswith('fact'):
            filter_on = (FactoidName.name,)
        elif search_type.startswith('value'):
            filter_on = (FactoidValue.value,)
        else:
            filter_on = (FactoidName.name, FactoidValue.value)

        if is_regex:
            filter_op = lambda x, y: x.op('REGEXP')(y)
        else:
            pattern = "%%%s%%" % escape_like_re.sub(r'\\\1', pattern)
            filter_op = lambda x, y: x.like(y)

        if len(filter_on) == 1:
            query = query.filter(filter_op(filter_on[0], pattern))
        else:
            query = query.filter(or_(filter_op(filter_on[0], pattern), filter_op(filter_on[1], pattern)))

        # Pre-evalute the iterable or the if statement will be True in SQLAlchemy 0.4 [Bug #383286]
        matches = [match for match in query[start:start+limit]]

        if matches:
            event.addresponse(u'; '.join(u'%s [%s]' % (unescape_name(fname.name), len(factoid.values)) for factoid, fname in matches))
        else:
            event.addresponse(u"I couldn't find anything with that name")

class Get(Processor, RPC):
    u"""<factoid> [( #<number> | /<pattern>/[r] )]"""
    feature = 'factoids'

    verbs = verbs
    priority = 900
    interrogatives = Option('interrogatives', 'Question words to strip', ('what', 'wtf', 'where', 'when', 'who', "what's", "who's"))
    date_format = Option('date_format', 'Format string for dates', '%Y/%m/%d')
    time_format = Option('time_format', 'Format string for times', '%H:%M:%S')

    def __init__(self, name):
        super(Get, self).__init__(name)
        RPC.__init__(self)

    def setup(self):
        self.get.im_func.pattern = re.compile(r'^(?:(?:%s)\s+(?:(%s)\s+)?)?(.+?)(?:\s+#(\d+))?(?:\s+/(.+?)/(r?))?$' % ('|'.join(self.interrogatives), '|'.join(self.verbs)), re.I)

    @handler
    def get(self, event, verb, name, number, pattern, is_regex):
        response = self.remote_get(name, number, pattern, is_regex, event)
        if response:
            event.addresponse(response)

    def remote_get(self, name, number=None, pattern=None, is_regex=None, event={}):
        factoid = get_factoid(event.session, name, number, pattern, is_regex)

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

            reply = reply.replace('$who', event.sender['nick'])
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
            reply = reply.replace('$unixtime', str(time()))

            (reply, count) = action_re.subn('', reply)
            if count:
                return {'action': True, 'reply': reply}

            (reply, count) = reply_re.subn('', reply)
            if count:
                return {'reply': reply}

            reply = u'%s %s' % (unescape_name(fname.name), reply)
            return reply

class Set(Processor):
    u"""<name> (<verb>|=<verb>=) [also] <value>"""
    feature = 'factoids'

    verbs = verbs
    priority = 910
    permission = u'factoid'
    
    def setup(self):
        self.set_factoid.im_func.pattern = re.compile(
            r'^(no[,.: ]\s*)?(.+?)\s+(?:=(\S+)=)?(?(3)|(%s))(\s+also)?\s+((?(3).+|(?!.*=\S+=).+))$'
            % '|'.join(self.verbs), re.I)

    @handler
    @authorise
    def set_factoid(self, event, correction, name, verb1, verb2, addition, value):
        verb = verb1 and verb1 or verb2

        factoid = event.session.query(Factoid).join(Factoid.names)\
                .filter(func.lower(FactoidName.name)==escape_name(name).lower()).first()
        if factoid:
            if correction:
                identities = get_identities(event)
                if not auth_responses(event, u'factoidadmin') and len(filter(lambda x: x.identity_id not in identities, factoid.values)) > 0:
                    return
                for fvalue in factoid.values:
                    event.session.delete(fvalue)
            elif not addition:
                event.addresponse(u'I already know stuff about %s', name)
                return
        else:
            factoid = Factoid()
            fname = FactoidName(escape_name(unicode(name)), event.identity)
            factoid.names.append(fname)
            event.session.save_or_update(factoid)
            event.session.flush()
            log.info(u"Creating factoid %s with name '%s' by %s", factoid.id, fname.name, event.identity)

        if not reply_re.match(value) and not action_re.match(value):
            value = '%s %s' % (verb, value)
        fvalue = FactoidValue(unicode(value), event.identity)
        factoid.values.append(fvalue)
        event.session.save_or_update(factoid)
        event.session.commit()
        log.info(u"Added value '%s' to factoid %s (%s) by %s/%s (%s)",
                fvalue.value, factoid.id, factoid.names[0].name,
                event.account, event.identity, event.sender['connection'])
        event.addresponse(True)

class Modify(Processor):
    u"""<name> [( #<number> | /<pattern>/[r] )] += <suffix>
    <name> [( #<number> | /<pattern>/[r] )] ~= ( s/<regex>/<replacement>/[g][i][r] | y/<source>/<dest>/ )"""
    feature = 'factoids'

    permission = u'factoid'
    permissions = (u'factoidadmin',)
    priority = 890

    @match(r'^(.+?)(?:\s+#(\d+)|\s+/(.+?)/(r?))?\s*\+=\s?(.+)$')
    @authorise
    def append(self, event, name, number, pattern, is_regex, suffix):
        factoids = get_factoid(event.session, name, number, pattern, is_regex, all=True)
        if len(factoids) == 0:
            if pattern:
                event.addresponse(u"I don't know about any %(name)s matching %(pattern)s", {
                    'name': name,
                    'pattern': pattern,
                })
            else:
                event.addresponse(u"I don't know about %s", name)
        elif len(factoids) > 1:
            event.addresponse(u"Pattern matches multiple factoids, please be more specific")
        else:
            factoidadmin = auth_responses(event, u'factoidadmin')
            identities = get_identities(event)
            factoid = factoids[0]

            if factoid[2].identity_id not in identities and not factoidadmin:
                return

            oldvalue = factoid[2].value
            factoid[2].value += suffix
            event.session.save_or_update(factoid[2])
            event.session.commit()

            log.info(u"Appended '%s' to value %s of factoid %s (%s) by %s/%s (%s)",
                    suffix, factoid[2].id, factoid[0].id, oldvalue, event.account,
                    event.identity, event.sender['connection'])
            event.addresponse(True)

    @match(r'^(.+?)(?:\s+#(\d+)|\s+/(.+?)/(r?))?\s*(?:~=|=~)\s*([sy](?P<sep>.).+(?P=sep).*(?P=sep)[gir]*)$')
    @authorise
    def modify(self, event, name, number, pattern, is_regex, operation, separator):
        factoids = get_factoid(event.session, name, number, pattern, is_regex, all=True)
        if len(factoids) == 0:
            if pattern:
                event.addresponse(u"I don't know about any %(name)s matching %(pattern)s", {
                    'name': name,
                    'pattern': pattern,
                })
            else:
                event.addresponse(u"I don't know about %s", name)
        elif len(factoids) > 1:
            event.addresponse(u"Pattern matches multiple factoids, please be more specific")
        else:
            factoidadmin = auth_responses(event, u'factoidadmin')
            identities = get_identities(event)
            factoid = factoids[0]

            if factoid[2].identity_id not in identities and not factoidadmin:
                return

            # Not very pythonistic, but escaping is a nightmare.
            parts = [[]]
            pos = 0
            while pos < len(operation):
                char = operation[pos]
                if char == separator:
                    parts.append([])
                elif char == u"\\":
                    if pos < len(operation) - 1:
                        if operation[pos+1] == u"\\":
                            parts[-1].append(u"\\")
                            pos += 1
                        elif operation[pos+1] == separator:
                            parts[-1].append(separator)
                            pos += 1
                        else:
                            parts[-1].append(u"\\")
                    else:
                        parts[-1].append(u"\\")
                else:
                    parts[-1].append(char)
                pos += 1

            parts = [u"".join(x) for x in parts]

            if len(parts) != 4:
                event.addresponse(u"That operation makes no sense. Try something like s/foo/bar/")
                return

            oldvalue = factoid[2].value
            op, search, replace, flags = parts
            flags = flags.lower()
            if op == "s":
                if "r" in flags:
                    if "i" in flags:
                        search += "(?i)"
                    try:
                        factoid[2].value = re.sub(search, replace, oldvalue, int("g" not in flags))
                    except:
                        event.addresponse(u"That operation makes no sense. Try something like s/foo/bar/")
                        return
                else:
                    newvalue = oldvalue.replace(search, replace, "g" in flags and -1 or 1)
                    if newvalue == oldvalue:
                        event.addresponse(u"I couldn't find '%(terms)s' in '%(oldvalue)s'. If that was a proper regular expression, append the 'r' flag", {
                            'terms': search,
                            'oldvalue': oldvalue,
                        })
                        return
                    factoid[2].value = newvalue

            elif op == "y":
                if len(search) != len(replace):
                    event.addresponse(u"That operation makes no sense. The source and destination must be the same length")
                    return
                try:
                    table = dict((ord(x), ord(y)) for x, y in zip(search, replace))
                    factoid[2].value = oldvalue.translate(table)

                except:
                    event.addresponse(u"That operation makes no sense. Try something like y/abcdef/ABCDEF/")
                    return

            event.session.save_or_update(factoid[2])
            event.session.commit()

            log.info(u"Applying '%s' to value %s of factoid %s (%s) by %s/%s (%s)",
                    operation, factoid[2].id, factoid[0].id, oldvalue, event.account, event.identity, event.sender['connection'])

            event.addresponse(True)

# vi: set et sta sw=4 ts=4:
