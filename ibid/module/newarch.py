import inspect

from ibid.module import Module
import re


class NewModule(Module):

    message = True
    addressed = True
    processed = False

    def process(self, event):
        if self.message and event.type != 'message':
            return

        if self.addressed and ('addressed' not in event or not event.addressed):
            return

        if not self.processed and event.processed:
            return

        for name, method in inspect.getmembers(self, inspect.ismethod):
            pattern = getattr(method, 'pattern', None)
            if pattern:
                match = pattern.search(event.message)
                if match is not None:
                    event = method(event, *match.groups()) or event

        return event

def match(regex):
    pattern = re.compile(regex, re.I)
    def wrap(function):
        setattr(function, 'pattern', pattern)
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
