# Copyright (c) 2011, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import datetime

import ibid.test
import ibid.utils

class TestUtils(ibid.test.TestCase):
    def test_ago(self):
        self.assertEqual(ibid.utils.ago(datetime.timedelta(seconds=60)), u'1 minute')
        self.assertEqual(ibid.utils.ago(datetime.timedelta(seconds=60000), 1), u'16 hours')

class CountryCodes(ibid.test.TestCase):
    network = True

    def setUp(self):
        super(CountryCodes, self).setUp()
        self.codes = ibid.utils.get_country_codes()

    def test_compound_countries(self):
        self.assertEqual(self.codes['SH'], u'Saint Helena, Ascension And Tristan Da Cunha')

    def test_of_countries(self):
        # Stored as Korea, Republic of
        self.assertEqual(self.codes['KR'], u'Republic Of Korea')
