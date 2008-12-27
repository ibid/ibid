import inspect
import re

import ibid

class Module(object):

    priority = 0

    def __init__(self, name):
        self.name = name

    def process(self, query):
        raise NotImplementedError

class Processor(object):

    type = 'message'
    addressed = True
    processed = False
    priority = 0

    def __init__(self, name):
        self.name = name
        if name in ibid.config.plugins:
            config = ibid.config.plugins[name]
            if 'addressed' in config:
                self.addressed = config['addressed']

        if self.processed and self.priority == 0:
            self.priority = 1500

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

def authorised(permission):
    def wrap(function):
        def new(self, event, *args):
            if not ibid.auth.authenticate(event):
                event.addresponse('You are not authenticated')
                return

            if not ibid.auth.authorise(event, permission):
                event.addresponse('You are not authorised')
                return

            return function(self, event, *args)
        return new
    return wrap

# vi: set et sta sw=4 ts=4:
