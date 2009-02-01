from inspect import getargspec, getmembers, ismethod, isclass
import re

from twisted.spread import pb
from twisted.web import xmlrpc, soap, resource
import simplejson

import ibid
from ibid.source.http import templates

class Option(object):

    def __init__(self, name, default=None, description=None):
        self.name = name
        self.default = default
        self.description = description

    def __get__(self, instance, owner):
        if instance.name in ibid.config.plugins and self.name in ibid.config.plugins[self.plugin]:
            return ibid.config.plugins[instance.name][self.name]
        else:
            return self.default

class Processor(object):

    type = 'message'
    addressed = True
    processed = False
    priority = 0

    def __init__(self, name):
        self.name = name

        if self.processed and self.priority == 0:
            self.priority = 1500

        self.load_config()

    def load_config(self):
        if self.name in ibid.config.plugins:
            config = ibid.config.plugins[self.name]

            for name, value in config.items():
                setattr(self, name, value)

        self.setup()

    def setup(self):
        pass

    def process(self, event):
        if event.type != self.type:
            return

        if self.addressed and ('addressed' not in event or not event.addressed):
            return

        if not self.processed and event.processed:
            return

        found = False
        for name, method in getmembers(self, ismethod):
            if hasattr(method, 'handler'):
                found = True
                if hasattr(method, 'pattern'):
                    match = method.pattern.search(event.message)
                    if match is not None:
                        if not hasattr(method, 'authorised') or auth_responses(event, self.permission):
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
    if not ibid.auth.authorise(event, permission):
        event.notauthed = True
        return False

    return True

def authorise(function):
    function.authorised = True
    return function

class RPC(pb.Referenceable, resource.Resource):
    isLeaf = True

    def __init__(self):
        ibid.rpc[self.feature] = self
        self.form = templates.get_template('plugin_form.html')
        self.list = templates.get_template('plugin_functions.html')

    def get_function(self, request):
        method = request.postpath[0]

        if hasattr(self, 'remote_%s' % method):
            return getattr(self, 'remote_%s' % method)

        return None

    def render_POST(self, request):
        args = []
        for arg in request.postpath[1:]:
            try:
                arg = simplejson.loads(arg)
            except ValueError, e:
                pass
            args.append(arg)

        kwargs = {}
        for key, value in request.args.items():
            try:
                value = simplejson.loads(value[0])
            except ValueError, e:
                value = value[0]
            kwargs[key] = value

        function = self.get_function(request)
        if not function:
            return "Not found"

        #self.log.debug(u'%s(%s, %s)', function, ', '.join([str(arg) for arg in args]), ', '.join(['%s=%s' % (k,v) for k,v in kwargs.items()]))

        try:
            result = function(*args, **kwargs)
            return simplejson.dumps(result)
        except Exception, e:
            return simplejson.dumps({'exception': True, 'message': e.message})

    def render_GET(self, request):
        function = self.get_function(request)
        if not function:
            functions = []
            for name, method in inspect.getmembers(self, inspect.ismethod):
                if name.startswith('remote_'):
                    functions.append(name.replace('remote_', '', 1))

            return self.list.render(object=self.feature, functions=functions).encode('utf-8')

        args, varargs, varkw, defaults = getargspec(function)
        del args[0]
        if len(args) == 0 or len(request.postpath) > 1 or len(request.args) > 0:
            return self.render_POST(request)

        return self.form.render(args=args).encode('utf-8')
 
# vi: set et sta sw=4 ts=4:
