# -*- coding: utf-8 -*-
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

    def test_string_transliterate(self):
        self.assertSucceeds('foo is bar quux')
        self.assertSucceeds('foo ~= y/a x/ ay/')
        self.assertResponseMatches('foo', 'foo isab raquuy')

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

    def test_search_case(self):
        # related to Bug #336247
        self.assertSucceeds('foo is bar QUUX')
        resp = r'foo \[1\]'
        self.assertResponseMatches('search for Foo', resp)
        self.assertResponseMatches('search for FoO', resp)
        self.assertResponseMatches('search for values Bar', resp)
        self.assertResponseMatches('search for Quux', resp)

    def test_modify_nothing(self):
        # test whether modifying a non-existent factoid vomits
        self.assertSucceeds('foo ~= s/lol/rofl/')

    def test_forget_wildcard(self):
        names = ['a $arg', '$args', '$arg', 'a $arg $arg']
        for name in names:
            self.assertSucceeds('%s is $1' % name)
            self.failIfResponseMatches('forget %s' % name, ".*didn't know")
            self.assertFails(name.replace('$arg', 'foo'))

    def test_unicode_name(self):
        names = [u'ascii', u'ü' , u'Ü', u'よし']
        for name in names:
            self.assertSucceeds('%s is foo' % name)
            self.assertResponseMatches(name, '%s is foo' % name)
            self.assertSucceeds('forget %s' % name)
            self.assertSucceeds('%s $arg is foo $1' % name)
            self.assertResponseMatches('%s baz' % name, '%s baz is foo baz' % name)
            self.assertSucceeds('forget %s $arg' % name)

    def test_search_unescape(self):
        self.assertSucceeds('slap $arg is <action>slaps $1')
        self.assertResponseMatches('search for slap',
            re.escape('slap $arg [1]'))
