# Copyright (c) 2009-2011, Jeremy Thurgood, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.
import logging

from twisted.python import log

import ibid


# Trial collects log output, so we feed ours logs into it.
class TwistedLogHandler(logging.Handler):
    def emit(self, record):
        log.msg(self.format(record))

logging.getLogger().addHandler(TwistedLogHandler())


class FakeConfig(dict):
    def __init__(self, basedict=None):
        if basedict is None: basedict = {}
        for name, value in basedict.iteritems():
            if isinstance(value, dict):
                value = FakeConfig(value)
            self[name] = value

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


def set_config(config):
    ibid.config = FakeConfig(config)


def run():
    "Run the Ibid test suite. Bit of a hack"
    from twisted.scripts.trial import run
    import sys
    sys.argv.append('ibid')
    run()

# vi: set et sta sw=4 ts=4:
