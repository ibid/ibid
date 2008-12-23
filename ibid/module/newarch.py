from ibid.module import Module
import re


class NewModule(Module):

    require_message = True
    require_message_addressed = True
    allow_processed = False
    match_regex = None

    def match(self, event):
        if self.match_regex is None:
            raise RuntimeException("match_regex not specified. Please fix this message, too.")
        matches = re.search(self.match_regex, event.message)
        if not matches:
            return None
        return matches.groups()

    def assert_require_message(self, event):
        if not self.require_message: return true
        return event.type == 'message'

    def assert_require_message_addressed(self, event):
        if not self.require_message_addressed: return true
        return (event.type == 'message'
                and event.addressed)

    def process(self, event):
        if not self.assert_require_message(event): return
        if not self.assert_require_message_addressed(event): return
        match = self.match(event)
        if match is None: return
        return self.handle_event(event, *match)

    def handle_event(self, event):
        raise NotImplementedError

class NewModuleTest1(NewModule):

    match_regex = r'test (foo|bar) (.*)'

    def handle_event(self, event, f_or_b, rest):
        if f_or_b == "foo":
            event.addresponse(u'Foo! [%s]' % rest)
        elif f_or_b == "bar":
            event.addresponse(u'Bar! <%s>' % rest)
        return event
