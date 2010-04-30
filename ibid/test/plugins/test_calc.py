# Copyright (c) 2010, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import logging

from ibid.test import PluginTestCase
from ibid.core import process

class CalcTest(PluginTestCase):
    load = ['calc']

    def test_basic(self):
        event = self.make_event(u'1+1')
        process(event, logging.getLogger())
        self.assertEquals(event.responses[0]['reply'], u'2')

    def test_too_big(self):
        event = self.make_event(u'100**100**100')
        process(event, logging.getLogger())
        self.assert_('big number' in event.respones[0]['reply'])
