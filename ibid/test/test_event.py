from twisted.trial import unittest

from ibid import event

class TestEvent(unittest.TestCase):
    def _ev(self, source='fakesource', type='testmessage'):
        return event.Event(source, type)

    def test_empty_event(self):
        ev = self._ev()
        self.assertEqual('fakesource', ev.source)
        self.assertEqual('testmessage', ev.type)
        self.assertEqual([], ev.responses)
        self.assertEqual({}, ev.sender)
        self.assertEqual(False, ev.processed)

    def test_attr(self):
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
        ev = self._ev()
        self.assertEqual([], ev.responses)
        self.assertRaises(Exception, lambda: ev.addresponse(None))
        self.assertEqual([], ev.responses)

    def test_str_response(self):
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse('foo')
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)
        self.assertEqual(True, ev.processed)

    def test_str_response_twice(self):
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

    def test_str_response_unprocessed(self):
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse('foo', processed=False)
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)
        self.assertEqual(False, ev.processed)

    def test_str_response_processed_unprocessed(self):
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

    def test_str_response_with_channel(self):
        ev = self._ev()
        ev.channel = '#chan'
        self.assertEqual([], ev.responses)
        ev.addresponse('foo')
        self.assertEqual([{'reply': 'foo',
                           'target': '#chan',
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)

    def test_unicode_response(self):
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse(u'foo')
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)

    def test_unicode_params_response(self):
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse(u'foo %(name)s', {'name': 'bar'})
        self.assertEqual([{'reply': 'foo bar',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)

    def test_unicode_tuple_params_response(self):
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse(u'foo %s', ('bar',))
        self.assertEqual([{'reply': 'foo bar',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)

    def test_simple_dict_response(self):
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse({'reply': 'foo'})
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], ev.responses)

    def test_complex_dict_response(self):
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
        ev = self._ev()
        self.assertEqual([], ev.responses)
        ev.addresponse('foo', bar='baz')
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True,
                           'bar': 'baz'}], ev.responses)

    def test_complex_dict_response(self):
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
