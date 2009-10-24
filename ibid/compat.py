"""
Compatibility functions for older versions of Python.
We support 2.4 <= x < 3.

Use this instead of:
* all
* any
* collections.defaultdict
* datetime.strptime
* email.utils
* hashlib
* (simple)json
* math.factorial
* xml.etree (cElementTree)
"""

import sys
(maj, min) = sys.version_info[:2]

if maj == 2 and min >= 5:
    from collections import defaultdict

    from datetime import datetime
    dt_strptime = datetime.strptime

    import email.utils as email_utils
    import hashlib
    from xml.etree import cElementTree as ElementTree

    all = all
    any = any

else:
    import cElementTree as ElementTree
    import email.Utils as email_utils

    def all(iterable):
        for element in iterable:
            if not element:
                return False
        return True

    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False

    class defaultdict(dict):
        def __init__(self, default_factory=None, *rest):
            dict.__init__(self, *rest)
            self.default_factory = default_factory

        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            value = self.default_factory()
            dict.__setitem__(self, key, value)
            return value

        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)

    import md5, sha
    class hashlib(object):
        @staticmethod
        def md5(x):
            return md5.new(x)

        @staticmethod
        def sha1(x):
            return sha.new(x)

        @staticmethod
        def sha224(x):
            class unsupported(object):
                @staticmethod
                def hexdigest():
                    return 'Not Supported'
            return unsupported

        sha512 = sha384 = sha224

    from datetime import datetime
    import time
    def dt_strptime(date_string, format):
        return datetime(*(time.strptime(date_string, format)[:6]))

if maj == 2 and min >= 6:
    import json
    from math import factorial

else:
    import simplejson as json

    def factorial(x):
        if not isinstance(x, int) or x < 0:
            raise ValueError
        if x == 0:
            return 1
        return reduce(lambda a, b: a * b, xrange(1, x + 1))

# vi: set et sta sw=4 ts=4:
