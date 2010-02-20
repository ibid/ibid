# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import inspect
import sys

import ibid
from ibid.plugins import Processor, match
from ibid.utils import human_join

features = {'help': {
    'description': u'Provides help and usage information about plugins.',
    'categories': ('admin', 'lookup',),
}}

class Help(Processor):
    u"""what can you do|help
    what can you <verb>|help <category>
    (how do I use|help|usage) <feature>
    features [for <word>]
    """
    feature = ('help',)

    def _get_features(self):
        """Walk the loaded processors and build dicts of categories and
        features in use. Dicts are cross-referenced by string.
        """
        processor_modules = set()
        categories = dict((k, {
            'description': v,
            'features': set(),
            'hidden': k in ibid.hidden_categories,
        }) for k, v in ibid.categories.iteritems())
        features = {}

        for processor in ibid.processors:
            for feature in getattr(processor, 'feature', []):
                if feature not in features:
                    features[feature] = {
                            'description': None,
                            'categories': set(),
                            'processors': set(),
                    }
                features[feature]['processors'].add(processor)
            processor_modules.add(sys.modules[processor.__module__])

        for module in processor_modules:
            for feature, meta in getattr(module, 'features', {}).iteritems():
                if feature not in features:
                    continue
                if meta.get('description'):
                    features[feature]['description'] = meta['description']
                for category in meta.get('categories', []):
                    features[feature]['categories'].add(category)
                    categories[category]['features'].add(feature)

        categories = dict((k, v) for k, v in categories.iteritems()
                                 if v['features'])
        return categories, features

    @match(r'^(?:help|what\s+(?:can|do)\s+you\s+do)$')
    def intro(self, event):
        categories, features = self._get_features()
        event.addresponse(u'I can: %s',
                          human_join(c['description'].lower()
                          for c in categories.itervalues()
                          if not c['hidden']))

    @match(r'^features$')
    def features(self, event):
        features = []

        for processor in ibid.processors:
            module = eval(processor.__module__)
            for feature in getattr(module, 'features', {}).keys():
                if feature not in features:
                    features.append(feature)

        event.addresponse(u'Features: %s',
                          human_join(sorted(features)) or u'none')

    @match(r'^help\s+(.+)$')
    def help(self, event, feature):
        feature = feature.lower()

        for processor in ibid.processors:
            module = eval(processor.__module__)
            if feature in getattr(module, 'features', []):
                desc = module.features[feature].get('description')
                if desc:
                    event.addresponse(desc)
                    return

        event.addresponse(u"I can't help you with %s", feature)

    @match(r'^(?:usage|how\s+do\s+I\s+use)\s+(.+)$')
    def usage(self, event, feature):
        feature = feature.lower()

        output = []
        for processor in ibid.processors:
            for name, klass in inspect.getmembers(processor, inspect.isclass):
                if (hasattr(klass, 'feature')
                        and feature in klass.feature
                        and klass.__doc__):
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
            if (hasattr(processor, 'feature')
                    and processor.__doc__
                    and phrase in processor.__doc__.lower()):
                matches.update(processor.feature)
            processor_modules.add(sys.modules[processor.__module__])

        for module in processor_modules:
            for feature, meta in getattr(module, 'features', {}).iteritems():
                if (phrase in feature
                        or phrase in meta.get('description', '').lower()):
                    matches.add(feature)

        return matches

# vi: set et sta sw=4 ts=4:
