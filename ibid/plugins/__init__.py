from copy import copy
from datetime import timedelta
from inspect import getargspec, getmembers, ismethod
import logging
import re

from twisted.spread import pb
from twisted.web import resource
try:
    from twisted.plugin import pluginPackagePaths
except ImportError:
    # Not available in Twisted 2.5.0 in Ubuntu hardy
    import os.path
    import sys
    def pluginPackagePaths(name):
        package = name.split('.')
        return [
            os.path.abspath(os.path.join(x, *package))
            for x
            in sys.path
            if
            not os.path.exists(os.path.join(x, *package + ['__init__.py']))]

import ibid
from ibid.compat import json

__path__.extend(pluginPackagePaths(__name__))

class Processor(object):
    """Base class for Ibid plugins.
    Processors receive events and (optionally) do things with them.

    Events are filtered in process() by to the following attributes:
    event_types: Only these types of events
    addressed: Require the bot to be addressed for public messages
    processed: Process events marked as already having been handled
    permission: The permission to check when calling @authorised handlers

    priority: Low priority Processors are handled first

    autoload: Load this Processor, when loading the plugin, even if not
    explicitly required in the configuration file
    """

    event_types = (u'message',)
    addressed = True
    processed = False
    priority = 0
    autoload = True

    __log = logging.getLogger('plugins')

    def __new__(cls, *args):
        if cls.processed and cls.priority == 0:
            cls.priority = 1500

        for name, option in options.items():
            new = copy(option)
            new.default = getattr(cls, name)
            setattr(cls, name, new)

        return super(Processor, cls).__new__(cls)

    def __init__(self, name):
        self.name = name
        self.setup()

    def setup(self):
        "Apply configuration. Called on every config reload"
        for name, method in getmembers(self, ismethod):
            if hasattr(method, 'run_every_config_key'):
                method.im_func.interval = timedelta(
                        seconds=getattr(self, method.run_every_config_key, 0))

    def shutdown(self):
        pass

    def process(self, event):
        "Process a single event"
        if event.type == 'clock':
            for name, method in getmembers(self, ismethod):
                if (hasattr(method, 'run_every')
                        and method.interval.seconds > 0
                        and not method.running):
                    method.im_func.running = True
                    if method.last_called is None:
                        # Don't fire first time
                        # Give sources a chance to connect
                        method.im_func.last_called = event.time
                    elif event.time - method.last_called >= method.interval:
                        method.im_func.last_called = event.time
                        try:
                            method(event)
                            if method.failing:
                                self.__log.info(u'No longer failing: %s.%s',
                                        self.__class__.__name__, name)
                                method.im_func.failing = False
                        except:
                            if not method.failing:
                                method.im_func.failing = True
                                self.__log.exception(
                                        u'Periodic method failing: %s.%s',
                                        self.__class__.__name__, name)
                            else:
                                self.__log.debug(u'Still failing: %s.%s',
                                        self.__class__.__name__, name)
                    method.im_func.running = False

        if event.type not in self.event_types:
            return

        if self.addressed and ('addressed' not in event or not event.addressed):
            return

        if not self.processed and event.processed:
            return

        found = False
        for name, method in getmembers(self, ismethod):
            if hasattr(method, 'handler'):
                if not hasattr(method, 'pattern'):
                    found = True
                    method(event)
                elif hasattr(event, 'message'):
                    found = True
                    match = method.pattern.search(
                            event.message[method.message_version])
                    if match is not None:
                        if (not getattr(method, 'auth_required', False)
                                or auth_responses(event, self.permission)):
                            method(event, *match.groups())
                        elif not getattr(method, 'auth_fallthrough', True):
                            event.processed = True

        if not found:
            raise RuntimeError(u'No handlers found in %s' % self)

        return event

# This is a bit yucky, but necessary since ibid.config imports Processor
from ibid.config import BoolOption, IntOption
options = {
    'addressed': BoolOption('addressed',
        u'Only process events if bot was addressed'),
    'processed': BoolOption('processed',
        u"Process events even if they've already been processed"),
    'priority': IntOption('priority', u'Processor priority'),
}

def handler(function):
    "Wrapper: Handle all events"
    function.handler = True
    function.message_version = 'clean'
    return function

def match(regex, version='clean'):
    "Wrapper: Handle all events where the message matches the regex"
    pattern = re.compile(regex, re.I | re.DOTALL)
    def wrap(function):
        function.handler = True
        function.pattern = pattern
        function.message_version = version
        return function
    return wrap

def auth_responses(event, permission):
    """Mark an event as having required authorisation, and return True if the
    event sender has permission.
    """
    if not ibid.auth.authorise(event, permission):
        event.complain = u'notauthed'
        return False

    return True

def authorise(fallthrough=True):
    """Require the permission specified in Processer.permission for the sender
    On failure, flags the event for Complain to respond appropriatly.
    If fallthrough=False, set the processed Flag to bypass later plugins.
    """
    def wrap(function):
        function.auth_required = True
        function.auth_fallthrough = fallthrough
        return function
    return wrap

def run_every(interval=0, config_key=None):
    "Wrapper: Run this handler every interval seconds"
    def wrap(function):
        function.run_every = True
        function.running = False
        function.last_called = None
        function.interval = timedelta(seconds=interval)
        if config_key is not None:
            function.run_every_config_key = config_key
        function.failing = False
        return function
    return wrap

from ibid.source.http import templates

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
                arg = json.loads(arg)
            except ValueError, e:
                pass
            args.append(arg)

        kwargs = {}
        for key, value in request.args.items():
            try:
                value = json.loads(value[0])
            except ValueError, e:
                value = value[0]
            kwargs[key] = value

        function = self.get_function(request)
        if not function:
            return "Not found"

        try:
            result = function(*args, **kwargs)
            return json.dumps(result)
        except Exception, e:
            return json.dumps({'exception': True, 'message': unicode(e)})

    def render_GET(self, request):
        function = self.get_function(request)
        if not function:
            functions = []
            for name, method in getmembers(self, ismethod):
                if name.startswith('remote_'):
                    functions.append(name.replace('remote_', '', 1))

            return self.list.render(object=self.feature, functions=functions) \
                    .encode('utf-8')

        args, varargs, varkw, defaults = getargspec(function)
        del args[0]
        if len(args) == 0 or len(request.postpath) > 1 or len(request.args) > 0:
            return self.render_POST(request)

        return self.form.render(args=args).encode('utf-8')

# vi: set et sta sw=4 ts=4:
