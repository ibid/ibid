# Copyright (c) 2009-2010, Jeremy Thurgood, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.
import logging

from twisted.python import log
from twisted.trial import unittest

import ibid
from ibid.event import Event
from ibid.db.models import Identity

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
    load_configured = False
    config = FakeConfig({'databases': {'ibid': 'sqlite:///test.db'},
                         'botname': 'bot'
                        })
    username = 'user'
    public = False

    def setUp(self):
        self._old_auth = ibid.auth
        ibid.auth = TestAuth()

        self._old_config = ibid.config
        # TODO: use fresh database
        self.config['database'] = 'sqlite:///test.db'
        ibid.config = self.config

        ibid.reload_reloader()
        ibid.reloader.reload_databases()
        ibid.reloader.reload_dispatcher()

        self.source = u'test_source_' + id(self)
        ibid.sources[self.source] = TestSource()

        load = self.load
        if self.load_base:
            load += ['admin', 'core']

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

    def make_event(self, message=None, type='message'):
        event = Event(self.source, type)
        event.sender['id'] = event.sender['connection'] = \
            event.sender['nick'] = self.username
        event.account = None
        event.addressed = not self.public
        event.public = self.public
        event.channel = u'testchan'

        if message is not None:
            event.message = message

    def tearDown(self):
        del ibid.sources[self.source]
        ibid.auth = self._old_auth
        ibid.config = self.old_config

# vi: set et sta sw=4 ts=4:
