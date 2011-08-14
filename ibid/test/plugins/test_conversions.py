# Copyright (c) 2010-2011, Max Rabkin, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import ibid.test

class UnihanTest(ibid.test.PluginTestCase):
    load = ['conversions']
    network = True

    def test_simp_trad(self):
        self.assertResponseMatches(u'unihan \u9A6C',
                                   u'.*the traditional form is \u99AC')
        self.assertResponseMatches(u'unihan \u99AC',
                                   u'.*the simplified form is \u9A6C')

class CurrencyLookupTest(ibid.test.TestCase):
    network = True

    def setUp(self):
        super(CurrencyLookupTest, self).setUp()
        from ibid.plugins import conversions
        self.processor = conversions.Currency(u'testplugin')

    def test_common_currencies(self):
        self.assertEqual(self.processor.resolve_currency('pound', True), 'GBP')
        self.assertEqual(self.processor.resolve_currency('dollar', True), 'USD')
        self.assertEqual(self.processor.resolve_currency('euro', True), 'EUR')
        self.assertEqual(self.processor.resolve_currency('rand', True), 'ZAR')

    def test_tld(self):
        self.assertEqual(self.processor.resolve_currency('.za', True), 'ZAR')
        self.assertEqual(self.processor.resolve_currency('.na', True), 'NAD')
        self.assertEqual(self.processor.resolve_currency('.ch', True), 'CHF')

    def test_country(self):
        self.assertEqual(self.processor.resolve_currency('united kingdom', True), 'GBP')
        self.assertEqual(self.processor.resolve_currency('south africa', True), 'ZAR')
        self.assertEqual(self.processor.resolve_currency('bosnia', True), 'BAM')
