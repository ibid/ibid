# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from copy import copy
import re
import sys

try:
    from Stemmer import Stemmer
except ImportError:
    from stemmer import PorterStemmer
    class Stemmer(PorterStemmer):
        def __init__(self, language):
            PorterStemmer.__init__(self)
        def stemWord(self, word):
            return PorterStemmer.stem(self, word, 0, len(word) - 1)

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
    help me with <category>
    how do I use <feature>
    help <(category|feature)>
    """
    feature = ('help',)
    stemmer = Stemmer('english')

    def _get_features(self):
        """Walk the loaded processors and build dicts of categories and
        features in use. Dicts are cross-referenced by string.
        """
        categories = {}
        for k, v in ibid.categories.iteritems():
            v = copy(v)
            v.update({
                'name': k,
                'features': set(),
            })
            categories[k] = v

        features = {}
        processor_modules = set()
        for processor in ibid.processors:
            for feature in getattr(processor, 'feature', []):
                if feature not in features:
                    features[feature] = {
                            'name': feature,
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

        usere = re.compile(r'[\s()[\]<>|]+')
        for name, feat in features.iteritems():
            feat['usage_keywords'] = frozenset(
                    self.stemmer.stemWord(word.strip())
                    for word in usere.split(u' '.join(feat['usage']))
                    if word.strip())
        for name, cat in categories.iteritems():
            cat['description_keywords'] = frozenset(self.stemmer.stemWord(word)
                    for word in cat['description'].lower().split())
        for name in features.keys():
            st_name = self.stemmer.stemWord(name)
            features[st_name] = features[name]
            if st_name != name:
                del features[name]
        for name in categories.keys():
            st_name = self.stemmer.stemWord(name)
            categories[st_name] = categories[name]
            if st_name != name:
                del categories[name]

        return categories, features

    def _describe_category(self, event, category):
        """Respond with the help information for a category"""
        event.addresponse(u'I use the following features for %(description)s: '
                          u'%(features)s\n'
                          u'Ask me "how do I use ..." for more details.',
            {
                'description': category['description'].lower(),
                'features': human_join(sorted(category['features'])),
            }, conflate=False)

    def _describe_feature(self, event, feature):
        """Respond with the help information for a feature"""
        output = []
        desc = feature['description']
        if desc is None:
            output.append(u'You can use it like this:')
        elif len(desc) > 100:
            output.append(desc)
            output.append(u'You can use it like this:')
        elif desc.endswith('.'):
            output.append(desc + u' You can use it like this:')
        else:
            output.append(desc + u'. You can use it like this:')

        for line in feature['usage']:
            output.append(u'  ' + line)

        event.addresponse(u'\n'.join(output), conflate=False)

    def _usage_search(self, event, terms, features):
        terms = frozenset(self.stemmer.stemWord(term) for term in terms)
        results = set()
        for name, feat in features.iteritems():
            if terms.issubset(feat['usage_keywords']):
                results.add(name)
        results = sorted(results)
        if len(results) == 1:
            self._describe_feature(event, features[results[0]])
        elif len(results) > 1:
            event.addresponse(
                u"Please be more specific. I don't know if you mean %s",
                human_join((features[result]['name'] for result in results),
                           conjunction=u'or'))
        else:
            event.addresponse(
                u"I'm afraid I don't know what you are asking about. "
                u'Ask "what can you do" to browse my features.')

    @match(r'^(?:help|features|what\s+(?:can|do)\s+you\s+do)$')
    def intro(self, event):
        categories, features = self._get_features()
        categories = filter(lambda c: c['weight'] is not None,
                            categories.itervalues())
        categories = sorted(categories, key=lambda c: c['weight'])
        event.addresponse(u'I can help you with: %s.\n'
                          u'Ask me "help me with ..." for more details.',
            human_join(c['description'].lower() for c in categories),
            conflate=False)

    @match(r'^help\s+(?:me\s+)?with\s+(.+)$')
    def describe_category(self, event, terms):
        categories, features = self._get_features()
        termset = frozenset(self.stemmer.stemWord(term)
                            for term in terms.lower().split())

        if len(termset) == 1:
            term = list(termset)[0]
            exact = [c for c in categories.itervalues() if c['name'] == term]
            if exact:
                self._describe_category(event, exact[0])
                return

        results = []
        for name, cat in categories.iteritems():
            if termset.issubset(cat['description_keywords']):
                results.append(name)

        if len(results) == 0:
            for name, cat in categories.iteritems():
                if terms.lower() in cat['description'].lower():
                    results.append(name)

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

        event.addresponse(u"I'm afraid I don't know what you are asking about. "
                          u'Ask "what can you do" to browse my features.')

    @match(r'^(?:help|usage|modinfo)\s+(\S+)$')
    def quick_help(self, event, terms):
        categories, features = self._get_features()
        terms = frozenset(terms.lower().split())
        if len(terms) == 1:
            term = list(terms)[0]
            exact = [c for c in categories.itervalues() if c['name'] == term]
            if exact:
                self._describe_category(event, exact[0])
                return
            exact = [f for f in features.itervalues() if f['name'] == term]
            if exact:
                self._describe_feature(event, exact[0])
                return

        self._usage_search(event, terms, features)

    @match(r'^how\s+do\s+I(?:\s+use)?\s+(.+)$')
    def describe_feature(self, event, feature):
        categories, features = self._get_features()

        feature = feature.lower()
        exact = [f for f in features.itervalues() if f['name'] == feature]
        if exact:
            self._describe_feature(event, exact[0])
        else:
            self._usage_search(event, frozenset(feature.split()), features)

    @match(r'^\s*(?:help\s+me\s+with|how\s+do\s+I(?:\s+use)?)\s+\.\.\.\s*$',
           version='deaddressed')
    def silly_people(self, event):
        event.addresponse(
                u'You must replace the ellipsis with the thing you are after')

# vi: set et sta sw=4 ts=4:
