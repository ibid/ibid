import csv

from mechanize import Browser, ParseError

from ibid.plugins import Processor, match
from ibid.utils import cacheable_download, human_join

"""
Dependancies:
    python-mechanize
"""

help = { u'airport' : u'Search for airports' }

airports_url = 'http://openflights.svn.sourceforge.net/viewvc/openflights/openflights/data/airports.dat'

airports = {}

def read_data():
    # File is listed as ISO 8859-1 (Latin-1) encoded on
    # http://openflights.org/data.html, but from decoding it appears to
    # actually be UTF8
    filename = cacheable_download(airports_url, 'flight/airports.dat')
    reader = csv.reader(open(filename), delimiter=',', quotechar='"')
    for row in reader:
        airports[int(row[0])] = [unicode(r, 'utf-8') for r in row[1:]]

def airport_search(query, search_loc = True):
    if not airports:
        read_data()
    if search_loc:
        query = [unicode(q) for q in query.lower().split(' ') if q]
    else:
        query = [unicode(query.lower())]
    ids = []
    for id, airport in airports.items():
        if search_loc:
            data = (' '.join(c.lower() for c in airport[:5])).split(' ')
        elif len(query[0]) == 3:
            data = [airport[3].lower()]
        else: # assume lenght 4 (won't break if not)
            data = [airport[4].lower()]
        if len(filter(lambda q: q in data, query)) == len(query):
            ids.append(id)
    return ids

def repr_airport(id):
    airport = airports[id]
    code = ''
    if airport[3] or airport[4]:
        code = ' (%s)' % u'/'.join(filter(lambda c: c, airport[3:5]))
    return '%s%s' % (airport[0], code)

class AirportSearch(Processor):
    """airport [in] <name|location|code>"""

    feature = 'airport'

    @match(r'^airports?\s+(in\s+)?(.+)$')
    def airport_search(self, event, search_loc, query):
        search_loc = search_loc is not None
        if not search_loc and not 3 <= len(query) <= 4:
            event.addresponse(u'Airport code must be 3 or 4 characters')
            return
        ids = airport_search(query, search_loc)
        if len(ids) == 0:
            event.addresponse(u"Sorry, I don't know that airport")
        elif len(ids) == 1:
            id = ids[0]
            airport = airports[id]
            code = 'unknown code'
            if airport[3] and airport[4]:
                code = 'codes %s and %s' % (airport[3], airport[4])
            elif airport[3]:
                code = 'code %s' % airport[3]
            elif airport[4]:
                code = 'code %s' % airport[4]
            event.addresponse(u'%s in %s, %s has %s' %
                    (airport[0], airport[1], airport[2], code))
        else:
            event.addresponse(u'Found the following airports: %s', human_join(repr_airport(id) for id in ids)[:480])

class FlightSearch(Processor):
    """flight from <departure> to <destination>"""

    feature = 'flight'

    travelocity_url = 'http://travel.travelocity.com/flights/InitialSearch.do'

    @match(r'flight\s+from\s+(.+)\s+to\s+(.+)')
    def flight_search(self, event, dpt, to):
        airport_dpt = airport_search(dpt)
        airport_to = airport_search(to)
        if len(airport_dpt) == 0:
            event.addresponse(u"Sorry, I don't know the airport you want to leave from")
            return
        if len(airport_to) == 0:
            event.addresponse(u"Sorry, I don't know the airport you want to fly to")
            return
        if len(airport_dpt) > 1:
            event.addresponse(u'The following airports match the departure: %s', human_join(repr_airport(id) for id in airport_dpt)[:480])
            return
        if len(airport_to) > 1:
            event.addresponse(u'The following airports match the destination: %s', human_join(repr_airport(id) for id in airport_to)[:480])
            return

        dpt = airport_dpt[0]
        to = airport_to[0]
        event.addresponse(u'Searching for flights from %s to %s', (repr_airport(dpt), repr_airport(to)))

        try:
            br = Browser()
            response = br.open(self.travelocity_url)
            br.select_form(name='AirSearchForm')
            br['leavingFrom'] = airports[dpt][3]
            br['goingTo'] = airports[to][3]
            br['leavingFrom1'] = '01/10/2010' # note mm/dd/yyy order
            br['goingTo1'] = '01/11/2010'
            response = br.submit()
            print response.read()
        except ParseError:
            event.addresponse(u'ParseError (need to fix!)')

# vi: set et sta sw=4 ts=4:
