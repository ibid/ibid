# Copyright (c) 2009-2011, Jeremy Thurgood, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.
import logging
import os
from tempfile import NamedTemporaryFile
from traceback import format_exception
import re

from twisted.python import log
from twisted.python.modules import getModule
from twisted.trial import unittest

import ibid
from ibid.core import process, DatabaseManager
from ibid.event import Event
from ibid.db import upgrade_schemas
from ibid.db.models import Identity
from ibid.config import FileConfig
from ibid.utils import locate_resource

# Trial collects log output, so we feed ours logs into it.
class TwistedLogHandler(logging.Handler):
    def emit(self, record):
        log.msg(self.format(record))

logging.getLogger().addHandler(TwistedLogHandler())


class FakeConfig(dict):
    def __init__(self, basedict=None):
        if basedict is None: basedict = {}
        for name, value in basedict.iteritems():
            if isinstance(value, dict):
                value = FakeConfig(value)
            self[name] = value

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


def set_config(config):
    ibid.config = FakeConfig(config)

class TestAuth(object):
    def authorise(self, event, permission):
        return True

class TestSource(object):
    type = 'test'
    permissions = []
    supports = ('action', 'multiline', 'notice')

    def setup(self):
        pass

    def logging_name(self, name):
        return name

    def truncation_point(self, response, event=None):
        return None

    def url(self):
        return None

class PluginTestCase(unittest.TestCase):
    load = []
    noload = []
    load_base = True
    load_configured = None
    username = u'user'
    public = False
    network = False

    def setUp(self):
        if self.network and os.getenv('IBID_NETWORKLESS_TEST') is not None:
            raise unittest.SkipTest('test uses network')

        ibid.config = FileConfig(locate_resource('ibid.test', 'test.ini'))

        if self.load_configured is None:
            self.load_configured = not self.load

        if self.load_base:
            self.load = self.load + ['core']
            self.noload = self.noload + ['core.RateLimit']

        self._create_database()

        ibid.reload_reloader()
        ibid.reloader.reload_databases()
        ibid.reloader.reload_dispatcher()
        ibid.reloader.load_processors(self.load, self.noload, self.load_configured)

        ibid.auth = TestAuth()
        self.source = u'test_source_' + unicode(id(self))
        ibid.sources[self.source] = TestSource()

        session = ibid.databases.ibid()

        self.identity = Identity(self.source, self.username)
        session.save(self.identity)
        session.commit()
        self.identity = session.query(Identity) \
            .filter_by(identity=self.username).one()

        session.close()

    def _create_database(self):
        # Make a temporary test database.
        # This assumes SQLite, both in the fact that the database is a single
        # file and in forming the URL.
        self.dbfile = NamedTemporaryFile(suffix='.db', prefix='ibid-test-')
        ibid.config['databases']['ibid'] = 'sqlite:///' + self.dbfile.name
        db = DatabaseManager(check_schema_versions=False, sqlite_synchronous=False)
        if self.load_configured:
            for module in getModule('ibid.plugins').iterModules():
                try:
                    __import__(module.name)
                except Exception, e:
                    print >> stderr, u"Couldn't load %s plugin: %s" % (
                            module.name.replace('ibid.plugins.', ''), unicode(e))
        else:
            for plugin in self.load:
                if plugin not in self.noload:
                    module = 'ibid.plugins.' + plugin
                    __import__(module)
        upgrade_schemas(db['ibid'])

    def make_event(self, message=None, type=u'message'):
        event = Event(self.source, type)
        event.sender['id'] = event.sender['connection'] = \
            event.sender['nick'] = self.username
        event.identity = self.identity.id
        event.account = None
        event.addressed = not self.public
        event.public = self.public
        event.channel = u'testchan'

        if message is not None:
            event.message = message

        return event

    def fail(self, message, event=None):
        if event is not None:
            message += '\n' + repr(event)
        unittest.TestCase.fail(self, message)

    def responseMatches(self, event, regex):
        if isinstance(event, basestring):
            event = self.make_event(event)
        process(event, logging.getLogger())

        if isinstance(regex, basestring):
            regex = re.compile(regex, re.U | re.I | re.DOTALL)

        for response in event.responses:
            if regex.match(response['reply']):
                return (True, event, response['reply'])
        else:
            return (False, event, event.responses)

    def assertResponseMatches(self, event, regex):
        match, event, resp = self.responseMatches(event, regex)
        if not match:
            self.fail("No response in matches regex %r" % regex, event)

    def failIfResponseMatches(self, event, regex):
        match, event, resp = self.responseMatches(event, regex)
        if match:
            self.fail("Response %r unexpectedly matches regex" % match, event)

    def assertSucceeds(self, event):
        if isinstance(event, basestring):
            event = self.make_event(event)
        process(event, logging.getLogger())

        self.assert_(event.get('processed', False))

        if 'complain' in event:
            self.fail("Event has complain set to %s" % event['complain'], event)

    def assertFails(self, event):
        if isinstance(event, basestring):
            event = self.make_event(event)
        process(event, logging.getLogger())

        self.assert_(event.get('processed', False))

        if event.get('processed', False) and 'complain' not in event:
            self.fail("Event was expected to fail", event)

    def tearDown(self):
        for processor in ibid.processors:
            processor.shutdown()
        del ibid.processors[:]

        del ibid.sources[self.source]
        ibid.databases.ibid().bind.engine.dispose()
        self.dbfile.close()

# vi: set et sta sw=4 ts=4:
