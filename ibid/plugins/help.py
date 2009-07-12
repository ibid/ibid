import inspect

import ibid
from ibid.plugins import Processor, match

help = {'help': u'Provides help and usage information about plugins.'}

class Help(Processor):
    u"""features
    help [<feature>]
    usage <feature>"""
    feature = 'help'

    @match(r'^help$')
    def intro(self, event):
        event.addresponse(u'Use "features" to get a list of available features. '
            u'"help <feature>" will give a description of the feature, and "usage <feature>" will describe how to use it.')

    @match(r'^features$')
    def features(self, event):
        features = []

        for processor in ibid.processors:
            module = eval(processor.__module__)
            if hasattr(module, 'help'):
                for feature in module.help.keys():
                    if feature not in features:
                        features.append(feature)

        event.addresponse(u'Features: %s', u' '.join(sorted(features)) or u'none')

    @match(r'^help\s+(.+)$')
    def help(self, event, feature):
        feature = feature.lower()

        for processor in ibid.processors:
            module = eval(processor.__module__)
            if hasattr(module, 'help') and feature in module.help:
                event.addresponse(module.help[feature])
                return

        event.addresponse(u"I can't help you with %s", feature)

    @match(r'^(?:usage|how\s+do\s+I\s+use)\s+(.+)$')
    def usage(self, event, feature):
        feature = feature.lower()

        for processor in ibid.processors:
            for name, klass in inspect.getmembers(processor, inspect.isclass):
                if hasattr(klass, 'feature') and klass.feature == feature and klass.__doc__:
                    for line in klass.__doc__.strip().splitlines():
                        event.addresponse(u'Usage: %s', line.strip())

        if not event.responses:
            event.addresponse(u"I don't know how to use %s either", feature)

# vi: set et sta sw=4 ts=4:
