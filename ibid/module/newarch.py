import inspect
import re

import ibid
from ibid.module import Module

class NewModule(Module):

    type = 'message'
    addressed = True
    processed = False

    def __init__(self, name):
        self.name = name
        if name in ibid.config.modules:
            config = ibid.config.modules[name]
            if 'addressed' in config:
                self.addressed = config['addressed']

    def process(self, event):
        if event.type != self.type:
            return

        if self.addressed and ('addressed' not in event or not event.addressed):
            return

        if not self.processed and event.processed:
            return

        found = False
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, 'pattern'):
                found = True
                match = method.pattern.search(event.message)
                if match is not None:
                    event = method(event, *match.groups()) or event

        if not found:
            raise RuntimeException(u'No handlers found in %s' % self)

        return event

def match(regex):
    pattern = re.compile(regex, re.I)
    def wrap(function):
        function.pattern = pattern
        return function
    return wrap

class NewModuleTest1(NewModule):

    @match(r'test foo (.*)')
    def handle_foo(self, event, rest):
        event.addresponse(u'Foo! [%s]' % rest)
        return event

    @match(r'test bar (.*)')
    def handle_bar(self, event, rest):
        event.addresponse(u'Bar! <%s>' % rest)
        return event
        
# vi: set et sta sw=4 ts=4:
