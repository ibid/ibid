import re

def addressed(function):
    @message
    def new(self, event):
        if not event.addressed:
            return
        return function(self, event)
    return new

def notprocessed(function):
    def new(self, event):
        if event.processed:
            return
        return function(self, event)
    return new

def message(function):
    def new(self, event):
        if event.type != 'message':
            return
        return function(self, event)
    return new

def match(regex):
    pattern = re.compile(regex, re.I)
    def wrap(function):
        @message
        def new(self, event):
            matches = pattern.search(event.message)
            if not matches:
                return
            return function(self, event, *matches.groups())
        return new
    return wrap

def addressedmessage(pattern=None):
    def wrap(function):
        @addressed
        @notprocessed
        def new(self, query):
            return function(self, query)
        if pattern:
            return match(pattern)(new)
        else:
            return new
    return wrap

# vi: set et sta sw=4 ts=4:
