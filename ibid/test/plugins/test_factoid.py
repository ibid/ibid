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
            self.failIfResponseMatches(name.replace('$arg', 'foo'),
                name.replace('$arg', 'foo') + 'is foo')

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

    def test_same_as_nothing(self):
        self.assertSucceeds('foo is the same as bar')
        self.assertResponseMatches('foo', "I don't know about bar")

    def test_multiple_copula(self):
        self.assertSucceeds('a is b =is= c')
        self.assertResponseMatches('a is b', 'a is b is c')
        self.assertSucceeds('a =is= b is c')
        self.assertResponseMatches('a', 'a is b is c')

    def test_name_punctuation(self):
        self.assertSucceeds('feegle? is fagle')
        self.assertResponseMatches('feegle?', 'feegle is fagle')
        self.assertResponseMatches('feegle', 'feegle is fagle')

    def test_duplicate_names(self):
        self.assertSucceeds('feegle is fagle')
        self.assertSucceeds('beagle is the same as feegle')
        self.assertResponseMatches('beagle is the same as feegle', '.*already')

    def test_also(self):
        self.assertSucceeds('foo is also bar')
        self.assertSucceeds('foo is also baz')
        self.assertSucceeds('foo also is quux')
        self.assertResponseMatches('literal foo', '.*bar.*baz.*quux')

    def test_wildcard_tamecard(self):
        self.assertSucceeds('foo a is bar')
        self.assertSucceeds('foo $arg is baz')
        self.assertResponseMatches('foo a', 'foo a is bar')
        self.assertResponseMatches('foo ack', 'foo ack is baz')

    def test_forget_multiple(self):
        self.assertSucceeds('foo is bar')
        self.assertSucceeds('foo is also baz')
        self.assertSucceeds('forget foo #2')
        self.assertResponseMatches('literal foo', '1: is bar')

    def test_get_case(self):
        self.assertSucceeds('Foo is bar')
        self.assertSucceeds('FoO $arg is lol')
        self.assertResponseMatches('foo', 'foo is bar')
        self.assertResponseMatches('foo lol', 'foo lol is lol')

    def test_empty(self):
        self.assertResponseMatches('. is foo', '.*empty')
        self.failIfResponseMatches('', '.*foo')
        self.failIfResponseMatches('.', '.*foo')
