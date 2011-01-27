# Copyright (c) 2011, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import re

from ibid.test import PluginTestCase

class FactoidTest(PluginTestCase):
    load = ['factoid']
    ack_re = '|'.join(map(re.escape, [u'If you say so',
                                        u'One learns a new thing every day',
                                        u"I'll remember that",
                                        u'Got it'])) + '$'

    def test_string_replace(self):
        # related to Bug #363865
        name = u'foo'
        value = 'x bar baz quux'
        needles = ['x ', 'x', 'baz', 'quux', ' quux', 'u', 'y']
        substs = ['', ' ', 'x', 'xx', 'u', 'uu']

        for needle in needles:
            for subst in substs:
                self.assertSucceeds('no, %s is %s' % (name, value))
                self.assertSucceeds('%s ~= s/%s/%s/' % (name, needle, subst))
                self.assertResponseMatches(name,
                    '%s is %s' % (name, value.replace(needle, subst, 1)))

                self.assertSucceeds('no, %s is %s' % (name, value))
                self.assertSucceeds('%s ~= s/%s/%s/g' % (name, needle, subst))
                self.assertResponseMatches(name,
                    '%s is %s' % (name, value.replace(needle, subst)))

                self.assertSucceeds('no, %s is %s' % (name, value))
                self.assertSucceeds('%s ~= s/%s/%s/i' %
                    (name, needle.upper(), subst))
                self.assertResponseMatches(name,
                    '%s is %s' % (name, value.replace(needle, subst, 1)))

    def test_append(self):
        name = u'foo'
        value = 'x bar baz quux'
        adds = ['x ', 'x', 'baz', 'quux', ' quux', 'u', 'y', '']

        for add in adds:
            self.assertResponseMatches('no, %s is %s' % (name, value), self.ack_re)
            self.assertResponseMatches('what is ' +name + '?', '%s is %s' % (name, value))
            self.assertSucceeds('%s +=%s' % (name, add))
            self.assertResponseMatches(name,
                '%s is %s' % (name, value+add))
