# Copyright (c) 2010, Jeremy Thurgood, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.
from inspect import stack

from twisted.trial import unittest

from ibid import event

class TestEvent(unittest.TestCase):
    def _ev(self, source='fakesource', type='testmessage'):
        return event.Event(source, type)

    def assertByteStringWarning(self, count=1):
        "Check that addresponse raised an error about using bytestrings"
        caller = getattr(self, stack()[1][3])
        warnings = self.flushWarnings(offendingFunctions=[caller])
        self.assertEqual(len(warnings), count)
        for i in range(count):
            self.assertTrue('byte string' in warnings[i]['message'],
                'Byte-String response should provoke a warning')

    def assertListSubstitutionWarning(self, count=1):
        "Check that addresponse raised an error about substituting lists"
        caller = getattr(self, stack()[1][3])
        warnings = self.flushWarnings(offendingFunctions=[caller])
        self.assertEqual(len(warnings), count)
        for i in range(count):
            self.assertTrue('single item or dict' in warnings[i]['message'],
                'Byte-String response should provoke a warning')

    def test_empty_event(self):
        "Events contain some default data."
        ev = self._ev()
        self.assertEqual('fakesource', ev.source)
        self.assertEqual('testmessage', ev.type)
        self.assertEqual([], ev.responses)
        self.assertEqual({}, ev.sender)
        self.assertEqual(False, ev.processed)

    def test_attr(self):
        "Attibutes and indexed keys are equivalent."
        ev = self._ev()
        self.assertRaises(AttributeError, lambda: ev.foo)
        self.assertRaises(KeyError, lambda: ev['foo'])
        ev.foo = 'bar'
        self.assertEqual('bar', ev.foo)
        self.assertEqual('bar', ev['foo'])
        self.assertRaises(AttributeError, lambda: ev.bar)
        self.assertRaises(KeyError, lambda: ev['bar'])
        ev['bar'] = 'foo'
        self.assertEqual('foo', ev.bar)
        self.assertEqual('foo', ev['bar'])

    def test_None_response(self):
        "None is an invalid response."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        self.assertRaises(Exception, lambda: ev.addresponse(None))
        self.assertEqual([], ev.responses)

    def test_str_response(self):
        "String responses become appropriate structures."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse('foo')
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)
        self.assertEqual(True, ev.processed)
        self.assertByteStringWarning()

    def test_str_response_twice(self):
        "Two responses are separate."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse('foo')
        ev.addresponse('bar')
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True},
                          {'reply': 'bar',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)
        self.assertEqual(True, ev.processed)
        self.assertByteStringWarning(2)

    def test_str_response_unprocessed(self):
        "Responses don't have to mark the event as processed."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse('foo', processed=False)
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)
        self.assertEqual(False, ev.processed)
        self.assertByteStringWarning(1)

    def test_str_response_processed_unprocessed(self):
        "processed=False doesn't clear the processed flag."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.processed = True
        ev.addresponse('foo', processed=False)
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)
        self.assertEqual(True, ev.processed)
        self.assertByteStringWarning(1)

    def test_str_response_with_channel(self):
        "Events from a channel send their responses back there."
        ev = self._ev()
        ev.channel = '#chan'
        self.assertEqual([], ev.responses)
        ev.addresponse('foo')
        self.assertEqual([{'reply': 'foo',
                           'target': '#chan',
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)
        self.assertByteStringWarning(1)

    def test_unicode_response(self):
        "Unicode responses behave the same as bytestrings."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse(u'foo')
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)

    def test_unicode_params_response(self):
        "Responses can contain parameters for dict-string interpolation."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse(u'foo %(name)s', {'name': 'bar'})
        self.assertEqual([{'reply': 'foo bar',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)

    def test_unicode_tuple_params_response(self):
        "Responses can contain parameters for tuple-string interpolation."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse(u'foo %s', ('bar',))
        self.assertEqual([{'reply': 'foo bar',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)
        self.assertListSubstitutionWarning()

    def test_simple_dict_response(self):
        "Dicts are valid response values."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse({'reply': 'foo'})
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)

    def test_complex_dict_response(self):
        "Dict responses can override event defaults."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse({'reply': 'foo',
                        'target': 'mytarget',
                        'source': 'mysource',
                        'address': False,
                        'conflate': False,
                        'mykey': 'myvalue'})
        self.assertEqual([{'reply': 'foo',
                           'target': 'mytarget',
                           'source': 'mysource',
                           'address': False,
                           'conflate': False,
                           'mykey': 'myvalue'}], ev.responses)

    def test_str_kwargs_response(self):
        "Keyword arguments to addresponse override event defaults."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse('foo', bar='baz')
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True,
                           'bar': 'baz'}], ev.responses)
        self.assertByteStringWarning(1)

    def test_complex_dict_with_kwargs_response(self):
        "Keyword arguments to addresponse override response dict values."
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse({'reply': 'r1',
                        'target': 't1',
                        'source': 's1',
                        'address': 'a1',
                        'conflate': 'c1'})
        ev.addresponse({'reply': 'r1',
                        'target': 't1',
                        'source': 's1',
                        'address': 'a1',
                        'conflate': 'c1'},
                       reply='r2',
                       target='t2',
                       source='s2',
                       address='a2',
                       conflate='c2')
        self.assertEqual([{'reply': 'r1',
                           'target': 't1',
                           'source': 's1',
                           'address': 'a1',
                           'conflate': 'c1'},
                          {'reply': 'r2',
                           'target': 't2',
                           'source': 's2',
                           'address': 'a2',
                           'conflate': 'c2'}], ev.responses)

# vi: set et sta sw=4 ts=4:
