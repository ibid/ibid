from twisted.trial import unittest
import ibid.test

# This needs to happen before we import core.
ibid.test.set_config({
        u'botname': u'test_ibid',
        u'plugins': {
            u'testplugin': {
                u'names': [u'test_ibid', u'bot', u'ant']
                },
            },
        })

from ibid.event import Event
from ibid.plugins import core

class TestAddressed(unittest.TestCase):

    def setUp(self):
        self.processor = core.Addressed(u'testplugin')

    def assert_addressed(self, event, addressed, message):
        self.assert_(hasattr(event, 'addressed'))
        self.assertEqual(event.addressed, addressed)
        self.assertEqual(event.message.strip(), message)

    def test_non_messages(self):
        for event_type in [u'timer', u'rpc']:
            event = Event(u'fakesource', event_type)
            event.message = u'bot: foo'
            self.processor.process(event)
            self.assertFalse(hasattr(event, u'addressed'))
            self.assertEqual(event.message, u'bot: foo')

    happy_prefixes = [
        (u'bot', u':  '),
        (u'ant', u', '),
        (u'test_ibid', u' '),
        ]

    def test_happy_prefix_names(self):
        for prefix in self.happy_prefixes:
            event = Event(u'fakesource', u'message')
            event.message = u'%s%sfoo' % prefix
            self.processor.process(event)
            self.assert_addressed(event, prefix[0], u'foo')

    sad_prefixes = [
        (u'botty', u': '),
        (u'spinach', u', '),
        (u'test-ibid', u' '),
        ]

    def test_sad_prefix_names(self):
        for prefix in self.sad_prefixes:
            event = Event(u'fakesource', u'message')
            event.message = u'%s%sfoo' % prefix
            self.processor.process(event)
            self.assert_addressed(event, False, u'%s%sfoo' % prefix)

    happy_suffixes = [
        (u', ', u'bot'),
        (u', \t ', u'ant'),
        (u' ,\t', u'test_ibid'),
        ]

    def test_happy_suffix_names(self):
        for suffix in self.happy_suffixes:
            event = Event(u'fakesource', u'message')
            event.message = u'foo%s%s' % suffix
            self.processor.process(event)
            self.assert_addressed(event, suffix[1], u'foo')

    sad_suffixes = [
        (u'. ', u'bot'),
        (u' ', u'ant'),
        (u', ', u'notbot'),
        (u', please ', u'bot'),
        ]

    def test_sad_suffix_names(self):
        for suffix in self.sad_suffixes:
            event = Event(u'fakesource', u'message')
            event.message = u'foo%s%s' % suffix
            self.processor.process(event)
            self.assert_addressed(event, False, u'foo%s%s' % suffix)
