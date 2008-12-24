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

        handlers = filter(lambda x: x.startswith('match_'), dir(self))

        if len(handlers) == 0:
            raise RuntimeException('No handlers defined')

        for regex in handlers:
            match = re.search(getattr(self, regex), event.message)
            if match is not None:
                event = getattr(self, regex.replace('match_', 'handle_', 1))(event, *match.groups()) or event

        return event

class NewModuleTest1(NewModule):

    match_foo = r'test foo (.*)'
    def handle_foo(self, event, rest):
        event.addresponse(u'Foo! [%s]' % rest)
        return event

    match_bar = r'test bar (.*)'
    def handle_bar(self, event, rest):
        event.addresponse(u'Bar! <%s>' % rest)
        return event
        
# vi: set et sta sw=4 ts=4:
