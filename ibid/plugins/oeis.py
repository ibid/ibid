# Copyright (c) 2009-2010, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from urllib2 import urlopen
import re
import logging

from ibid.compat import defaultdict
from ibid.plugins import Processor, match
from ibid.utils import plural

log = logging.getLogger('plugins.oeis')

features = {'oeis': {
    'description': 'Query the Online Encyclopedia of Integer Sequences',
    'categories': ('lookup', 'web', 'calculate',),
}}
class OEIS(Processor):
    usage = u"""oeis (A<OEIS number>|M<EIS number>|N<HIS number>)
    oeis <term>[, ...]"""

    features = ('oeis',)

    @match(r'^oeis\s+([AMN]\d+|-?\d(?:\d|-|,|\s)*)$')
    def oeis (self, event, query):
        query = re.sub(r'(,|\s)+', ',', query)
        f = urlopen('http://oeis.org/search?n=1&fmt=text&q='
                    + query)

        for i in range(3):
            f.next() # the first lines are uninteresting
        results_m = re.search(r'Showing .* of (\d+)', f.next())
        if results_m:
            f.next()
            sequence = Sequence(f)
            event.addresponse(u'%(name)s - %(url)s - %(values)s',
                                {'name': sequence.name,
                                 'url': sequence.url(),
                                 'values': sequence.values})

            results = int(results_m.group(1))
            if results > 1:
                event.addresponse(u'There %(was)s %(count)d more %(results)s. '
                                  u'See %(url)s%(query)s for more.',
                    {'was': plural(results-1, 'was', 'were'),
                     'count': results-1,
                     'results': plural(results-1, 'result', 'results'),
                     'url': 'http://oeis.org/search?q=',
                     'query': query})
        else:
            event.addresponse(u"I couldn't find that sequence.")

class Sequence(object):
    def __init__ (self, lines):
        cmds = defaultdict(list)
        for line in lines:
            line = line.lstrip()[:-1]
            if not line:
                break

            line_m = re.match(r'%([A-Z]) (A\d+)(?: (.*))?$', line)
            if line_m:
                cmd, self.catalog_num, info = line_m.groups()
                cmds[cmd].append(info)
            else:
                cmds[cmd][-1] += line

        # %V, %W and %X give signed values if the sequence is signed.
        # Otherwise, only %S, %T and %U are given.
        self.values = (''.join(cmds['V'] + cmds['W'] + cmds['X']) or
                        ''.join(cmds['S'] + cmds['T'] + cmds['U']))

        self.name = ''.join(cmds['N'])

    def url (self):
        return 'http://oeis.org/' + self.catalog_num

# vi: set et sta sw=4 ts=4:
