# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from time import sleep

import ibid
from ibid.plugins import Processor, match, authorise

features = {'test': {
    'description': u'Test functions for use in bot development',
    'categories': ('debug',),
}}

class Tests(Processor):
    u"""delay <seconds>
    authorise <permission>
    email <address>
    raise exception
    topic <topic>
    """
    feature = ('test',)
    permission = u'debug'

    @match(r'^delay\s+(\d+\.?\d*)$')
    @authorise()
    def sleep(self, event, delay):
        sleep(float(delay))
        event.addresponse(True)

    @match(r'^authorise\s+(\S+)$')
    def is_authorised(self, event, permission):
        if ibid.auth.authorise(event, permission):
            event.addresponse(u'Yes')
        else:
            event.addresponse(u'No')

    @match(r'^email\s+(.+)$')
    @authorise()
    def email(self, event, address):
        event.addresponse(u'Test message', source='email', target=unicode(address))
        event.addresponse(u"I've emailed %s", address)

    @match(r'^raise\s+exception$')
    @authorise()
    def throw_up(self, event):
        raise Exception("Ow, that hurt.")

    @match(r'^topic\s+(.+)$')
    @authorise()
    def topic(self, event, topic):
        event.addresponse(topic, topic=True, address=False)

# vi: set et sta sw=4 ts=4:
