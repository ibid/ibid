# collections.defaultdict only in Python 2.5
try:
    from collections import defaultdict
except ImportError:
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

# email.Utils was renamed in Python 2.5
try:
    import email.utils as email_utils
except ImportError:
    import email.Utils as email_utils

# hashlib only in Python >= 2.5
try:
    import hashlib
except ImportError:
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

# xml.etree only in Python >= 2.5
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    import cElementTree as ElementTree

# math.factorial only in Python >= 2.6
try:
    from math import factorial
except ImportError:
    def factorial(x):
        if not isinstance(x, int) or x < 0:
            raise ValueError
        if x == 0:
            return 1
        return reduce(lambda a, b: a * b, xrange(1, x + 1))

# json only in Python >= 2.6
try:
    import simplejson as json
except ImportError:
    import json

# vi: set et sta sw=4 ts=4:
