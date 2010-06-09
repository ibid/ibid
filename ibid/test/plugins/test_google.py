# Copyright (c) 2010, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from ibid.test import PluginTestCase

class GDefineTest(PluginTestCase):
    load = ['google']
    network = True

    def test_basic(self):
        words = u'puppy Kojien'.split()
        for word in words:
            self.assertSucceeds(u'gdefine ' + word)

    def test_unicode_latin(self):
        words = [u'na\N{latin small letter i with diaeresis}ve',
                 u'K\N{latin small letter o with macron}jien']
        for word in words:
            self.assertSucceeds(u'gdefine ' + word)
