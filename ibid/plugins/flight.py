import csv

from ibid.config import Option
from ibid.plugins import Processor, match
from ibid.utils import human_join

# TODO help

class AirportSearch(Processor):
    # TODO docstring

    feature = 'airport'

    airports_file = Option('airports_file', 'File containing airports data', 'ibid/data/airports.dat')

    def setup(self):
        # File is listed as ISO 8859-1 (Latin-1) encoded on
        # http://openflights.org/data.html, but from decoding it appears to
        # actually be UTF8
        reader = csv.reader(open(self.airports_file), delimiter=',', quotechar='"')
        self.airports = {}
        for row in reader:
            self.airports[int(row[0])] = [unicode(r, 'utf-8') for r in row[1:]]

    def _airport_search(self, query):
        query = [unicode(q) for q in query.lower().split(' ') if q]
        ids = []
        for id, airport in self.airports.items():
            data = (' '.join(c.lower() for c in airport[:5])).split(' ')
            if len(filter(lambda q: q in data, query)) == len(query):
                ids.append(id)
        return ids

    @match(r'^airports?\s+(?:in\s+)?(.+)$')
    def airport_search(self, event, query):
        ids = self._airport_search(query)
        if len(ids) == 0:
            event.addresponse(u"Sorry, I don't know that airport")
        elif len(ids) == 1:
            id = ids[0]
            airport = self.airports[id]
            code = 'unknown code'
            if airport[4] and airport[5]:
                code = 'codes %s and %s' % (airport[3], airport[4])
            elif airport[4]:
                code = 'code %s' % airport[3]
            elif airport[5]:
                code = 'code %s' % airport[4]
            event.addresponse(u'%s in %s, %s has %s' %
                    (airport[0], airport[1], airport[2], code))
        else:
            results = []
            for id in ids:
                airport = self.airports[id]
                code = ''
                if airport[3] or airport[4]:
                    code = ' (%s)' % u'/'.join(filter(lambda c: c, airport[3:5]))
                results.append('%s%s' % (airport[0], code))
            event.addresponse(u'Found the following airports: %s', human_join(results)[:480])

# vi: set et sta sw=4 ts=4:
