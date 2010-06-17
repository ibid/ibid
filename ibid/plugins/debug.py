# Copyright (c) 2010, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from random import choice
from traceback import format_exception, format_exception_only

from ibid.plugins import Processor, match, authorise

features = {'debug': {
    'description': u'Help track bugs in the bot',
    'categories': ('debug',),
}}

last_exc_info = None

class SetLastException(Processor):
    # Come after everything. We don't modify events, and we want to catch
    # exceptions even in post-processors.
    priority = 10000

    def process(self, event):
        global last_exc_info

        if 'exc_info' in event:
            last_exc_info = event.exc_info

class LastException(Processor):
    features = (u'debug',)
    usage = u"""last exception
    last traceback"""

    permission = u'debug'

    @match(r'^last\s+(exception|trac[ek]back)$')
    @authorise()
    def exception(self, event, kind):
        if last_exc_info is None:
            event.addresponse(choice((u'Are you *looking* for trouble?',
                                      u"I'll make an exception for you.")))
        else:
            if kind.lower() == 'exception':
                lines = format_exception_only(*last_exc_info[:2])
            else:
                lines = format_exception(*last_exc_info)
            event.addresponse(unicode(''.join(lines)[:-1]), conflate=False)
