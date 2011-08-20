# Copyright (c) 2011, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import datetime

import ibid.test
import ibid.utils

class TestUtils(ibid.test.TestCase):
    def test_ago(self):
        self.assertEqual(ibid.utils.ago(datetime.timedelta(seconds=60)), u'1 minute')
        self.assertEqual(ibid.utils.ago(datetime.timedelta(seconds=60000), 1), u'16 hours')

class TestUtilsNetwork(ibid.test.TestCase):
    network = True

    def test_get_country_codes(self):
        codes = ibid.utils.get_country_codes()
        self.assertIn('ZA', codes)
