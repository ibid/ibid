"""Sample module for the new plugin architecture."""

import inspect
import re

import ibid
from ibid.plugins import Processor, match

class NewModuleTest1(Processor):
    """Processor to test the new module architecture"""

    @match(r'test foo (.*)')
    def handle_foo(self, event, rest):
        """test foo <text>"""
        event.addresponse(u'Foo! [%s]' % rest)
        return event

    @match(r'test bar (.*)')
    def handle_bar(self, event, rest):
        """test bar <text>"""
        event.addresponse(u'Bar! <%s>' % rest)
        return event
        
# vi: set et sta sw=4 ts=4:
