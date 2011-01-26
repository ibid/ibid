# Copyright (c) 2010-2011, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from ibid.test import PluginTestCase

class UnihanTest(PluginTestCase):
    load = ['conversions']
    network = True

    def test_simp_trad(self):
        self.assertResponseMatches(u'unihan \u9A6C',
                                   u'.*the traditional form is \u99AC')
        self.assertResponseMatches(u'unihan \u99AC',
                                   u'.*the simplified form is \u9A6C')
