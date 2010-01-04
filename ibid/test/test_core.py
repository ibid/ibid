from datetime import datetime, timedelta

from twisted.trial import unittest
from twisted.internet import defer, reactor

import ibid.test
import ibid
from ibid import core, event


class TestProcessor(object):
    """
    A processor object stub.
    """
    name = 'testprocessor'

    def __init__(self, proc_func):
        self.proc_func = proc_func

    def process(self, event):
        self.proc_func(event)


class TestSource(object):
    """
    A source object stub.
    """
    def __init__(self):
        self._msgs = []

    def send(self, response):
        self._msgs.append(response)


class TestDispatcher(unittest.TestCase):
    """
    Test the Dispatcher class.
    """

    def setUp(self):
        ibid.processors[:] = []
        ibid.sources.clear()
        self.dispatcher = core.Dispatcher()

    def tearDown(self):
        ibid.processors[:] = []
        ibid.sources.clear()

    def _add_processor(self, proc_func):
        "Add a processor to the dispatch chain."
        ibid.processors.append(TestProcessor(proc_func))

    def _ev(self, source='fakesource', type='testmessage'):
        "Create an event with some default values."
        return event.Event(source, type)

    def _defer_assertions(self, callback, result, delay=0.000001):
        "Create a deferred to assert things that only happen later."
        dfr = defer.Deferred()
        dfr.addCallback(callback, self)
        reactor.callLater(delay, dfr.callback, result)
        return dfr

    def _dispatch_and_assert(self, callback, ev):
        """
        Dispatch an event and add an assertion callback to the
        resulting deferred.
        """
        dfr = self.dispatcher.dispatch(ev)
        dfr.addCallback(callback, self)
        return dfr

    def test_process_no_processors(self):
        "With no processors, an event is unmodified."
        ev = self._ev()
        pev = self.dispatcher._process(ev)
        self.assertEqual(ev, pev)
        self.assertEqual([], pev.responses)

    def test_dispatch_no_processors(self):
        "With no processors, an event is unmodified."
        ev = self._ev()
        def _cb(_ev, _self):
            _self.assertEqual(ev, _ev)
            _self.assertEqual([], _ev.responses)
        return self._dispatch_and_assert(_cb, ev)

    def test_process_noop_processor(self):
        "A passive processor is called, but does not modify."
        ev = self._ev()
        procs = [0]
        def prc(e):
            procs[0] += 1
        self._add_processor(prc)
        pev = self.dispatcher._process(ev)
        self.assertEqual(ev, pev)
        self.assertEqual([], pev.responses)
        self.assertEqual([1], procs)
        self.assertEqual(False, pev.processed)
    
    def test_dispatch_noop_processor(self):
        "A passive processor is called, but does not modify the event."
        ev = self._ev()
        procs = [0]
        def prc(e):
            procs[0] += 1
        self._add_processor(prc)
        def _cb(_ev, _self):
            _self.assertEqual(ev, _ev)
            _self.assertEqual([], _ev.responses)
            _self.assertEqual([1], procs)
            _self.assertEqual(False, _ev.processed)
        return self._dispatch_and_assert(_cb, ev)

    def test_process_simple_reply(self):
        "A processor can add a reply."
        ev = self._ev()
        def prc(e):
            e.addresponse('foo')
        self._add_processor(prc)
        pev = self.dispatcher._process(ev)
        self.assertEqual(ev, pev)
        self.assertTrue('complain' not in pev)
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], pev.responses)
        self.assertEqual(True, pev.processed)

    def test_dispatch_simple_reply(self):
        "A processor can add a reply."
        ev = self._ev()
        def prc(e):
            e.addresponse('foo')
        self._add_processor(prc)
        def _cb(_ev, _self):
            _self.assertEqual(ev, _ev)
            _self.assertTrue('complain' not in _ev)
            _self.assertEqual([{'reply': 'foo',
                                'target': None,
                                'source': 'fakesource',
                                'address': True,
                                'conflate': True}], _ev.responses)
            _self.assertEqual(True, _ev.processed)
        return self._dispatch_and_assert(_cb, ev)

    def test_process_broken_processor(self):
        "If a processor dies, we complain and carry on."
        ev = self._ev()
        def prc(e):
            assert False
        self._add_processor(prc)
        pev = self.dispatcher._process(ev)
        self.assertEqual(ev, pev)
        self.assertEqual('exception', pev.complain)
        self.assertEqual([], pev.responses)
        self.assertEqual(True, pev.processed)

    def test_dispatch_broken_processor(self):
        "If a processor dies, we complain and carry on."
        ev = self._ev()
        def prc(e):
            assert False
        self._add_processor(prc)
        def _cb(_ev, _self):
            _self.assertEqual(ev, _ev)
            _self.assertEqual('exception', _ev.complain)
            _self.assertEqual([], _ev.responses)
            _self.assertEqual(True, _ev.processed)
        return self._dispatch_and_assert(_cb, ev)

    def test_process_double_reply(self):
        "We can add multiple replies to an event."
        ev = self._ev()
        def prc(e):
            e.addresponse('foo')
            e.addresponse('bar')
        self._add_processor(prc)
        pev = self.dispatcher._process(ev)
        self.assertEqual(ev, pev)
        self.assertTrue('complain' not in pev)
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True},
                          {'reply': 'bar',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], pev.responses)
        self.assertEqual(True, pev.processed)

    def test_dispatch_double_reply(self):
        "We can add multiple replies to an event."
        ev = self._ev()
        def prc(e):
            e.addresponse('foo')
            e.addresponse('bar')
        self._add_processor(prc)
        def _cb(_ev, _self):
            _self.assertEqual(ev, _ev)
            _self.assertTrue('complain' not in _ev)
            _self.assertEqual([{'reply': 'foo',
                                'target': None,
                                'source': 'fakesource',
                                'address': True,
                                'conflate': True},
                               {'reply': 'bar',
                                'target': None,
                                'source': 'fakesource',
                                'address': True,
                                'conflate': True}], _ev.responses)
            _self.assertEqual(True, _ev.processed)
        return self._dispatch_and_assert(_cb, ev)

    def test_process_reply_send_invalid_source(self):
        "Messages to invalid sources get silently swallowed."
        ev = self._ev()
        def prc(e):
            e.addresponse('foo')
            e.addresponse('bar', source='testsource')
        self._add_processor(prc)
        pev = self.dispatcher._process(ev)
        self.assertEqual(ev, pev)
        self.assertTrue('complain' not in pev)
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], pev.responses)
        self.assertEqual(True, pev.processed)

    def test_dispatch_reply_send_invalid_source(self):
        "Messages to invalid sources get silently swallowed."
        ev = self._ev()
        def prc(e):
            e.addresponse('foo')
            e.addresponse('bar', source='testsource')
        self._add_processor(prc)
        def _cb(_ev, _self):
            _self.assertEqual(ev, _ev)
            _self.assertTrue('complain' not in _ev)
            _self.assertEqual([{'reply': 'foo',
                                'target': None,
                                'source': 'fakesource',
                                'address': True,
                                'conflate': True}], _ev.responses)
            self.assertEqual(True, _ev.processed)
        return self._dispatch_and_assert(_cb, ev)

    def test_process_reply_send_valid_source(self):
        "Messages to other sources get sent."
        src = TestSource()
        ibid.sources['testsource'] = src
        ev = self._ev()
        def prc(e):
            e.addresponse('foo')
            e.addresponse('bar', source='testsource')
        self._add_processor(prc)
        pev = self.dispatcher._process(ev)
        self.assertEqual(ev, pev)
        self.assertTrue('complain' not in pev)
        self.assertEqual([{'reply': 'foo',
                           'target': None,
                           'source': 'fakesource',
                           'address': True,
                           'conflate': True}], pev.responses)
        self.assertEqual(True, pev.processed)
        def _cb(_src, _self):
            _self.assertEqual([{'reply': 'bar',
                                'target': None,
                                'source': 'testsource',
                                'address': True,
                                'conflate': True}], _src._msgs)
        return self._defer_assertions(_cb, src)

    def test_dispatch_reply_send_valid_source(self):
        "Messages to other sources get sent."
        src = TestSource()
        ibid.sources['testsource'] = src
        ev = self._ev()
        def prc(e):
            e.addresponse('foo')
            e.addresponse('bar', source='testsource')
        self._add_processor(prc)
        def _cb(_ev, _self):
            _self.assertEqual(ev, _ev)
            _self.assertTrue('complain' not in _ev)
            _self.assertEqual([{'reply': 'foo',
                                'target': None,
                                'source': 'fakesource',
                                'address': True,
                                'conflate': True}], _ev.responses)
            _self.assertEqual(True, _ev.processed)
            _self.assertEqual([{'reply': 'bar',
                                'target': None,
                                'source': 'testsource',
                                'address': True,
                                'conflate': True}], src._msgs)
        return self._dispatch_and_assert(_cb, ev)

    def test_call_later_no_args(self):
        "Calling later should call stuff later."
        ev = self._ev()
        ev.channel = None
        ev.public = None
        dfr = defer.Deferred()
        tm = datetime.now()
        def _cl(_ev):
            _ev.did_stuff = True
            dfr.callback(_ev)
        def _cb(_ev, _self, _oev):
            _self.assertTrue(tm + timedelta(seconds=0.01) < datetime.now())
            _self.assertTrue(_ev.did_stuff)
            _self.assertFalse(hasattr(_oev, 'did_stuff'))
        dfr.addCallback(_cb, self, ev)
        self.dispatcher.call_later(0.01, _cl, ev)
        return dfr

    def test_call_later_args(self):
        "Calling later should call stuff later."
        ev = self._ev()
        ev.channel = None
        ev.public = None
        dfr = defer.Deferred()
        tm = datetime.now()
        def _cl(_ev, val):
            _ev.did_stuff = val
            dfr.callback(_ev)
        def _cb(_ev, _self, _oev):
            _self.assertTrue(tm + timedelta(seconds=0.01) < datetime.now())
            _self.assertEqual('thingy', _ev.did_stuff)
            _self.assertFalse(hasattr(_oev, 'did_stuff'))
        dfr.addCallback(_cb, self, ev)
        self.dispatcher.call_later(0.01, _cl, ev, 'thingy')
        return dfr

    def test_call_later_kwargs(self):
        "Calling later should call stuff later."
        ev = self._ev()
        ev.channel = None
        ev.public = None
        dfr = defer.Deferred()
        tm = datetime.now()
        def _cl(_ev, val='default'):
            _ev.did_stuff = val
            dfr.callback(_ev)
        def _cb(_ev, _self, _oev):
            _self.assertTrue(tm + timedelta(seconds=0.01) < datetime.now())
            _self.assertEqual('thingy', _ev.did_stuff)
            _self.assertFalse(hasattr(_oev, 'did_stuff'))
        dfr.addCallback(_cb, self, ev)
        self.dispatcher.call_later(0.01, _cl, ev, val='thingy')
        return dfr

# vi: set et sta sw=4 ts=4:
