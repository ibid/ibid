import inspect
import re

import ibid

class Processor(object):

    type = 'message'
    addressed = True
    processed = False
    priority = 0

    def __init__(self, name):
        self.name = name

        if self.processed and self.priority == 0:
            self.priority = 1500

        if name in ibid.config.plugins:
            config = ibid.config.plugins[name]

            for name, value in config.items():
                setattr(self, name, value)

    def process(self, event):
        if event.type != self.type:
            return

        if self.addressed and ('addressed' not in event or not event.addressed):
            return

        if not self.processed and event.processed:
            return

        found = False
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, 'handler'):
                found = True
                if hasattr(method, 'pattern'):
                    match = method.pattern.search(event.message)
                    if match is not None:
                        event = method(event, *match.groups()) or event
                else:
                    event = method(event) or event

        if not found:
            raise RuntimeError(u'No handlers found in %s' % self)

        return event

def handler(function):
    function.handler = True
    return function

def match(regex):
    pattern = re.compile(regex, re.I)
    def wrap(function):
        function.handler = True
        function.pattern = pattern
        return function
    return wrap

def auth_responses(event, permission):
    if not ibid.auth.authenticate(event):
        event.addresponse('You are not authenticated')
        return False

    if not ibid.auth.authorise(event, permission):
        event.addresponse('You are not authorised')
        return False

    return True

def authorise(permission):
    def wrap(function):
        def new(self, event, *args):
            if auth_responses(event, permission):
                return function(self, event, *args)
        return new
    return wrap

# vi: set et sta sw=4 ts=4:
