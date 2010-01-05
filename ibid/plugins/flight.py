import csv
from xml.etree import ElementTree
import re
from urllib import urlencode

from ibid.config import IntOption
from ibid.plugins import Processor, match
from ibid.utils import cacheable_download, human_join
from ibid.utils.html import get_html_parse_tree

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
            data = (u' '.join(c.lower() for c in airport[:5])).split(' ')
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

class Flight:
    def __init__(self):
        self.airline, self.flight, self.depart_time, self.depart_ap, self.arrive_time, \
                self.arrive_ap, self.duration, self.stops, self.price = \
                None, None, None, None, None, None, None, None, None

    def int_price(self):
        return int(self.price[1:])

    def int_duration(self):
        hours, minutes = 0, 0
        match = re.search(r'(\d+)hr', self.duration)
        if match:
            hours = int(match.group(1))
        match = re.search(r'(\d+)min', self.duration)
        if match:
            minutes = int(match.group(1))
        return int(hours)*60 + int(minutes)

class FlightSearch(Processor):
    """flights from <departure> to <destination>
    cheapest flight from <departure> to <destination>
    quickest flight from <departure> to <destination>"""

    feature = 'flight'

    travelocity_url = 'http://www.travelocity.com/resolve/default?show=n'
    max_results = IntOption('max_results', 'Maximum number of results to list', 5)

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

        params = {}
        params['leavingFrom'] = airports[dpt][3]
        params['goingTo'] = airports[to][3]
        params['leavingDate'] = '01/10/2010' # note mm/dd/yyy order
        params['returningDate'] = '01/11/2010'
        etree = get_html_parse_tree('http://travel.travelocity.com/flights/InitialSearch.do', data=urlencode(params), treetype='etree')
        while True:
            script = [script for script in etree.getiterator('script')][1]
            matches = script.text and re.search(r'var finurl = "(.*)"', script.text)
            if matches:
                url = 'http://travel.travelocity.com/flights/%s' % matches.group(1)
                etree = get_html_parse_tree(url, treetype='etree')
            else:
                break

        flights = []
        table = [t for t in etree.getiterator('table')][3]
        trs = [t for t in table.getiterator('tr')]
        for tr1, tr2 in zip(trs[1::2], trs[2::2]):
            tds = [t for t in tr1.getiterator('td')] + [t for t in tr2.getiterator('td')]
            flight = Flight()
            for td in tds:
                if td.get(u'class').strip() == u'tfAirline':
                    anchor = td.find('a')
                    if anchor is not None:
                        flight.airline = anchor.text.strip()
                    else:
                        flight.airline = td.text.split('\n')[0].strip()
                    flight.flight = td.find('div').text.strip()
                if td.get(u'class').strip() == u'tfDepart' and td.text:
                    flight.depart_time = td.text.split('\n')[0].strip()
                    flight.depart_ap = '%s %s' % (td.find('div').text.strip(),
                            td.find('div').find('span').text.strip())
                if td.get(u'class').strip() == u'tfArrive' and td.text:
                    flight.arrive_time = td.text.split('\n')[0].strip()
                    span = td.find('span')
                    if span is not None and span.get(u'class').strip() == u'tfNextDayDate':
                        flight.arrive_time = u'%s %s' % (flight.arrive_time, span.text.strip()[2:])
                        span = [s for s in td.find('div').getiterator('span')][1]
                        flight.arrive_ap = '%s %s' % (td.find('div').text.strip(),
                                span.text.strip())
                    else:
                        flight.arrive_ap = '%s %s' % (td.find('div').text.strip(),
                                td.find('div').find('span').text.strip())
                if td.get(u'class').strip() == u'tfTime' and td.text:
                    flight.duration = td.text.strip()
                    flight.stops = td.find('span').find('a').text.strip()
                if td.get(u'class').strip() in [u'tfPrice', u'tfPriceOr'] and td.text:
                    flight.price = td.text.strip()
            flights.append(flight)

        return flights

    @match(r'^flights?\s+from\s+(.+)\s+to\s+(.+)$')
    def list_flights(self, event, dpt, to):
        flights = self.flight_search(event, dpt, to)
        if flights is None:
            return
        if len(flights) == 0:
            event.addresponse(u'No matching flights found')
            return
        for flight in flights[:self.max_results]:
            event.addresponse('%s %s departing %s from %s, arriving %s at %s (flight time %s, %s) costs %s per person',
                    (flight.airline, flight.flight, flight.depart_time, flight.depart_ap, flight.arrive_time,
                        flight.arrive_ap, flight.duration, flight.stops, flight.price))
        if len(flights) > self.max_results:
            event.addresponse(u"and at least %i more flights, which I haven't returned", len(flights) - self.max_results)
            return

    @match(r'^cheapest flight\s+from\s+(.+)\s+to\s+(.+)$')
    def cheapest_flight(self, event, dpt, to):
        flights = self.flight_search(event, dpt, to)
        if flights is None:
            return
        if len(flights) == 0:
            event.addresponse(u'No matching flights found')
            return
        flights.sort(cmp=lambda a, b: a.int_price() < b.int_price())
        flight = flights[0]
        event.addresponse('%s %s departing %s from %s, arriving %s at %s (flight time %s, %s) costs %s per person',
                (flight.airline, flight.flight, flight.depart_time, flight.depart_ap, flight.arrive_time,
                    flight.arrive_ap, flight.duration, flight.stops, flight.price))

    @match(r'^quickest flight\s+from\s+(.+)\s+to\s+(.+)$')
    def cheapest_flight(self, event, dpt, to):
        flights = self.flight_search(event, dpt, to)
        if flights is None:
            return
        if len(flights) == 0:
            event.addresponse(u'No matching flights found')
            return
        flights.sort(cmp=lambda a, b: a.int_duration() < b.int_duration())
        flight = flights[0]
        event.addresponse('%s %s departing %s from %s, arriving %s at %s (flight time %s, %s) costs %s per person',
                (flight.airline, flight.flight, flight.depart_time, flight.depart_ap, flight.arrive_time,
                    flight.arrive_ap, flight.duration, flight.stops, flight.price))


# vi: set et sta sw=4 ts=4:
