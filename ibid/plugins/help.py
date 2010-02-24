# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from copy import copy
import sys

import ibid
from ibid.plugins import Processor, match
from ibid.utils import human_join

features = {'help': {
    'description': u'Provides help and usage information about plugins.',
    'categories': ('admin', 'lookup',),
}}

class Help(Processor):
    usage = u"""
    what can you do|help
    what can you <verb>
    how do I use <feature>
    help <(category|feature)>
    """
    feature = ('help',)

    def _get_features(self):
        """Walk the loaded processors and build dicts of categories and
        features in use. Dicts are cross-referenced by string.
        """
        categories = {}
        for k, v in ibid.categories.iteritems():
            v = copy(v)
            v.update({'features': set(),})
            categories[k] = v

        features = {}
        processor_modules = set()
        for processor in ibid.processors:
            for feature in getattr(processor, 'feature', []):
                if feature not in features:
                    features[feature] = {
                            'description': None,
                            'categories': set(),
                            'processors': set(),
                            'usage': [],
                    }
                features[feature]['processors'].add(processor)
                if hasattr(processor, 'usage'):
                    features[feature]['usage'] += [line.strip()
                            for line in processor.usage.split('\n')
                            if line.strip()]
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

    def _describe_category(self, event, category):
        """Respond with the help information for a category"""
        event.addresponse(u'I can %(description)s with: %(features)s\n'
                          u'Ask me "how do I use ..." for more details.',
            {
                'description': category['description'].lower(),
                'features': human_join(category['features']),
            }, conflate=False)

    def _describe_feature(self, event, feature):
        """Respond with the help information for a feature"""
        output = []
        desc = feature['description']
        if desc is None:
            output.append(u'Usage:')
        elif len(desc) > 100:
            output.append(desc)
            output.append(u'Usage:')
        elif desc.endswith('.'):
            output.append(desc + u' Usage:')
        else:
            output.append(desc + u'. Usage:')

        output += feature['usage']

        event.addresponse(u'\n'.join(output), conflate=False)

    def _usage_search(self, event, terms, features):
        results = set()
        for k, v in features.iteritems():
            for line in v['usage']:
                if terms.issubset(frozenset(line.split())):
                    results.add(k)
        results = sorted(results)
        if len(results) == 1:
            self._describe_feature(event, features[results[0]])
        elif len(results) > 1:
            event.addresponse(
                u"Please be more specific. I don't know if you mean %s",
                human_join(results, conjunction=u'or'))
        else:
            event.addresponse(
                u"I'm afraid I don't know what you are asking about. "
                u'Ask "what can you do" to browse my features')

    @match(r'^(?:help|features|what\s+(?:can|do)\s+you\s+do)$')
    def intro(self, event):
        categories, features = self._get_features()
        categories = filter(lambda c: c['weight'] is not None,
                            categories.itervalues())
        categories = sorted(categories, key=lambda c: c['weight'])
        event.addresponse(
            u'I can: %s\nAsk me "what ... can you ..." for more details',
            human_join(c['description'].lower() for c in categories),
            conflate=False)

    @match(r'^what\s+(.+\s+)?can\s+you\s+(.+)$')
    def describe_category(self, event, terms1, terms2):
        # Don't stomp on intro
        if terms2.lower() == u'do':
            return

        categories, features = self._get_features()
        if terms1 is None:
            terms1 = u''
        terms = frozenset(terms1.lower().split() + terms2.lower().split())

        if len(terms) == 1:
            term = list(terms)[0]
            if term in categories:
                self._describe_category(event, categories[term])
                return

        results = []
        for cat, meta in categories.iteritems():
            if terms.issubset(frozenset(meta['description'].lower().split())):
                results.append(cat)

        if len(results) == 0:
            for cat, meta in categories.iteritems():
                if (terms1.lower() in meta['description'].lower()
                        and terms2.lower() in meta['description'].lower()):
                    results.append(cat)

        results.sort()
        if len(results) == 1:
            self._describe_category(event, categories[results[0]])
            return
        elif len(results) > 1:
            event.addresponse(
                    u"Please be more specific, I don't know if you mean %s.",
                    human_join(('%s (%s)'
                                % (categories[r]['description'].lower(), r)
                                for r in results),
                               conjunction=u'or'))
            return

        event.addresponse(u"I'm afraid I don't know what you are asking about")

    @match(r'^(?:help|usage|modinfo)\s+(.+)$')
    def quick_help(self, event, terms):
        categories, features = self._get_features()
        terms = frozenset(terms.lower().split())
        if len(terms) == 1:
            term = list(terms)[0]
            if term in categories:
                self._describe_category(event, categories[term])
                return
            if term in features:
                self._describe_feature(event, features[term])
                return

        self._usage_search(event, terms, features)

    @match(r'^how\s+do\s+I(?:\s+use)?\s+(.+)$')
    def describe_feature(self, event, feature):
        categories, features = self._get_features()

        feature = feature.lower()
        if feature in features:
            self._describe_feature(event, features[feature])
        else:
            self._usage_search(event, frozenset(feature.split()), features)

    @match(r'\s*(?:what\s+can\s+you|how\s+do\s+I(?:\s+use)?)\s+\.\.\.\s*',
           version='deaddressed')
    def silly_people(self, event):
        event.addresponse(
                u'You must replace the ellipsis with the thing you are after')

# vi: set et sta sw=4 ts=4:
