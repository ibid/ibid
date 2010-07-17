# Copyright (c) 2009-2010, Jeremy Thurgood, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.
import logging
from shutil import copyfile
import os
from tempfile import mkstemp
import re

from twisted.python import log
from twisted.trial import unittest

import ibid
from ibid.core import process
from ibid.event import Event
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

        ibid.auth = TestAuth()

        ibid.config = FileConfig(locate_resource('ibid.test', 'test.ini'))

        # Make a temporary copy of the test database.
        # This assumes SQLite, both in the fact that the database is a single
        # file and in forming the URL.
        self.dbfile = mkstemp('.db', 'ibid-test-')[1]
        ibid.config['databases']['ibid'] = 'sqlite:///' + self.dbfile
        copyfile(locate_resource('ibid.test', 'test.db'), self.dbfile)

        ibid.reload_reloader()
        ibid.reloader.reload_databases()
        ibid.reloader.reload_dispatcher()

        self.source = u'test_source_' + unicode(id(self))
        ibid.sources[self.source] = TestSource()

        if self.load_configured is None:
            self.load_configured = not self.load

        load = self.load
        if self.load_base:
            load += ['core']

        ibid.reloader.load_processors(load, self.noload, self.load_configured)

        session = ibid.databases.ibid()

        identity = session.query(Identity).filter_by(identity=self.username,
                                                     source=self.source).first()
        if not identity:
            identity = Identity(self.source, self.username)
            session.save(identity)
            session.commit()
            self.identity = session.query(Identity) \
                                .filter_by(identity=self.username).first()
        self.identity_id = self.identity.id

        session.close()

    def make_event(self, message=None, type=u'message'):
        event = Event(self.source, type)
        event.sender['id'] = event.sender['connection'] = \
            event.sender['nick'] = self.username
        event.identity = self.identity_id
        event.account = None
        event.addressed = not self.public
        event.public = self.public
        event.channel = u'testchan'

        if message is not None:
            event.message = message

        return event

    def responseMatches(self, event, regex):
        if isinstance(event, basestring):
            event = self.make_event(event)
        process(event, logging.getLogger())

        if isinstance(regex, basestring):
            regex = re.compile(regex, re.U | re.I | re.DOTALL)

        for response in event.responses:
            if regex.match(response['reply']):
                return True
        else:
            return False

    def assertResponseMatches(self, event, regex):
        if not self.responseMatches(event, regex):
            self.fail("No response matches regex")

    def failIfResponseMatches(self, event, regex):
        if self.responseMatches(event, regex):
            self.fail("Response unexpectedly matches regex")

    def assertSucceeds(self, event):
        if isinstance(event, basestring):
            event = self.make_event(event)
        process(event, logging.getLogger())

        self.assert_(event.get('processed', False))

        if 'complain' in event:
            self.fail("Event has complain set to %s" % event['complain'])

    def assertFails(self, event):
        if isinstance(event, basestring):
            event = self.make_event(event)
        process(event, logging.getLogger())

        self.assert_(event.get('processed', False))

        if event.get('processed', False) and 'complain' not in event:
            self.fail("Event was expected to fail")

    def tearDown(self):
        del ibid.sources[self.source]
        os.remove(self.dbfile)

# vi: set et sta sw=4 ts=4:
