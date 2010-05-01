# Copyright (c) 2010, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from ibid.test import PluginTestCase

class CalcTest(PluginTestCase):
    load = ['calc']

    def test_basic(self):
        self.assertResponseMatches(u'1+1', '2$')

    def test_too_big(self):
        self.assertResponseMatches(u'100**100**100', '.*big number.*')
