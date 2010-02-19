# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import inspect
import sys

import ibid
from ibid.plugins import Processor, match
from ibid.utils import human_join

features = {'help': u'Provides help and usage information about plugins.'}

class Help(Processor):
    u"""features [for <word>]
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
            for feature in getattr(module, 'features', {}).keys():
                if feature not in features:
                    features.append(feature)

        event.addresponse(u'Features: %s', human_join(sorted(features)) or u'none')

    @match(r'^help\s+(.+)$')
    def help(self, event, feature):
        feature = feature.lower()

        for processor in ibid.processors:
            module = eval(processor.__module__)
            if feature in getattr(module, 'features', []):
                event.addresponse(module.features[feature])
                return

        event.addresponse(u"I can't help you with %s", feature)

    @match(r'^(?:usage|how\s+do\s+I\s+use)\s+(.+)$')
    def usage(self, event, feature):
        feature = feature.lower()

        output = []
        for processor in ibid.processors:
            for name, klass in inspect.getmembers(processor, inspect.isclass):
                if hasattr(klass, 'feature') and klass.feature == feature and klass.__doc__:
                    for line in klass.__doc__.strip().splitlines():
                        output.append(line.strip())

        if len(output) == 1:
            event.addresponse(u'Usage: %s', output[0])
        elif len(output) > 1:
            event.addresponse(
                u"You can use %(feature)s in the following ways:\n%(usage)s", {
                    'feature': feature,
                    'usage': u'\n'.join(output)
                }, conflate=False)
        else:
            event.addresponse(u"I don't know how to use %s either", feature)

    @match(r'^features\s+(?:for|with)\s+(.*)$')
    def search (self, event, phrase):
        features = map(unicode, self._search(phrase))
        features.sort()
        if len(features) == 0:
            event.addresponse(u"I couldn't find that feature.")
        elif len(features) == 1:
            event.addresponse(
                u'The "%s" feature might be what you\'re looking for.',
                features[0])
        else:
            event.addresponse(u"Are you looking for %s?",
                            human_join(features, conjunction='or'))

    def _search (self, phrase):
        phrase = phrase.lower()
        matches = set()
        processor_modules = set()
        for processor in ibid.processors:
            if (hasattr(processor, 'feature') and processor.__doc__ and
                phrase in processor.__doc__.lower()):
                matches.add(processor.feature)
            processor_modules.add(sys.modules[processor.__module__])

        for module in processor_modules:
            for feature, help in getattr(module, 'features', {}).iteritems():
                if phrase in feature or phrase in help.lower():
                    matches.add(feature)

        return matches

# vi: set et sta sw=4 ts=4:
