import csv
import re
from sys import maxint
from urllib import urlencode
from xml.etree import ElementTree

from dateutil.parser import parse

from ibid.config import IntOption
from ibid.plugins import Processor, match
from ibid.utils import cacheable_download, human_join
from ibid.utils.html import get_html_parse_tree

help = { u'airport' : u'Search for airports',
         u'flight'  : u'Search for flights on travelocity' }

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
        ids = airport_search(query, False)
        if len(ids) == 1:
            return ids
        query = [unicode(q) for q in query.lower().split(' ') if q]
    else:
        query = [unicode(query.lower())]
    ids = []
    for id, airport in airports.items():
        if search_loc:
            data = (u' '.join(c.lower() for c in airport[:5])).split(' ')
        elif len(query[0]) == 3:
            data = [airport[3].lower()]
        else: # assume length 4 (won't break if not)
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

    @match(r'^airports?\s+((?:in|for)\s+)?(.+)$')
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
        self.flight, self.depart_time, self.depart_ap, self.arrive_time, \
                self.arrive_ap, self.duration, self.stops, self.price = \
                [], None, None, None, None, None, None, None

    def int_price(self):
        try:
            return int(self.price[1:])
        except ValueError:
            return maxint

    def int_duration(self):
        hours, minutes = 0, 0
        match = re.search(r'(\d+)hr', self.duration)
        if match:
            hours = int(match.group(1))
        match = re.search(r'(\d+)min', self.duration)
        if match:
            minutes = int(match.group(1))
        return int(hours)*60 + int(minutes)

MONTH_SHORT = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
MONTH_LONG = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')
OTHER_STUFF = ('am', 'pm', 'st', 'nd', 'rd', 'th', 'morning', 'afternoon', 'evening', 'anytime')
DATE = r'(?:[0-9.:/hT -]|%s)+' % '|'.join(MONTH_SHORT+MONTH_LONG+OTHER_STUFF)

class FlightException(Exception):
    pass

class FlightSearch(Processor):
    """[<cheapest|quickest>] flight from <departure> to <destination> from <depart_date> [anytime|morning|afternoon|evening|<time>] to <return_date> [anytime|morning|afternoon|evening|<time>]"""

    feature = 'flight'

    max_results = IntOption('max_results', 'Maximum number of results to list', 5)

    def _flight_search(self, event, dpt, to, dep_date, ret_date):
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

        def to_travelocity_date(date):
            date = date.lower()
            time = None
            for period in ['anytime', 'morning', 'afternoon', 'evening']:
                if period in date:
                    time = period.title()
                    date = date.replace(period, '')
                    break
            date = parse(date)
            if time is None:
                if date.hour == 0 and date.minute == 0:
                    time = 'Anytime'
                else:
                    time = date.strftime('%I:00')
                    if time[0] == '0':
                        time = time[1:]
                    if date.hour < 12:
                        time += 'am'
                    else:
                        time += 'pm'
            date = date.strftime('%m/%d/%Y')
            return (date, time)

        (dep_date, dep_time) = to_travelocity_date(dep_date)
        (ret_date, ret_time) = to_travelocity_date(ret_date)

        params = {}
        params['leavingFrom'] = airports[dpt][3]
        params['goingTo'] = airports[to][3]
        params['leavingDate'] = dep_date
        params['dateLeavingTime'] = dep_time
        params['returningDate'] = ret_date
        params['dateReturningTime'] = ret_time
        etree = get_html_parse_tree('http://travel.travelocity.com/flights/InitialSearch.do', data=urlencode(params), treetype='etree')
        while True:
            script = [script for script in etree.getiterator('script')][1]
            matches = script.text and re.search(r'var finurl = "(.*)"', script.text)
            if matches:
                url = 'http://travel.travelocity.com/flights/%s' % matches.group(1)
                etree = get_html_parse_tree(url, treetype='etree')
            else:
                break

        # Handle error
        div = [d for d in etree.getiterator('div') if d.get(u'class') == 'e_content']
        if len(div):
            error = div[0].find('h3').text
            raise FlightException(error)

        departing_flights = self._parse_travelocity(etree)
        return_url = None
        table = [t for t in etree.getiterator('table')][3]
        for tr in table.getiterator('tr'):
            for td in tr.getiterator('td'):
                if td.get(u'class').strip() in ['tfPrice', 'tfPriceOrButton']:
                    div = td.find('div')
                    if div is not None:
                        button = div.find('button')
                        if button is not None:
                            onclick = button.get('onclick')
                            match = re.search(r"location.href='\.\./flights/(.+)'", onclick)
                            url_page = match.group(1)
                            match = re.search(r'^(.*?)[^/]*$', url)
                            url_base = match.group(1)
                            return_url = url_base + url_page

        etree = get_html_parse_tree(return_url, treetype='etree')
        returning_flights = self._parse_travelocity(etree)

        return (departing_flights, returning_flights, url)

    def _parse_travelocity(self, etree):
        flights = []
        table = [t for t in etree.getiterator('table') if t.get(u'id') == 'tfGrid'][0]
        trs = [t for t in table.getiterator('tr')]
        tr_index = 1
        while tr_index < len(trs):
            tds = []
            while True:
                new_tds = [t for t in trs[tr_index].getiterator('td')]
                tds.extend(new_tds)
                tr_index += 1
                if len(filter(lambda t: t.get(u'class').strip() == u'tfAirlineSeatsMR', new_tds)):
                    break
            flight = Flight()
            for td in tds:
                if td.get(u'class').strip() == u'tfAirline':
                    anchor = td.find('a')
                    if anchor is not None:
                        airline = anchor.text.strip()
                    else:
                        airline = td.text.split('\n')[0].strip()
                    flight.flight.append(u'%s %s' % (airline, td.find('div').text.strip()))
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
            flight.flight = human_join(flight.flight)
            flights.append(flight)

        return flights

    @match(r'^(?:(cheapest|quickest)\s+)?flights?\s+from\s+(.+)\s+to\s+(.+)\s+from\s+(%s)\s+to\s+(%s)$' % (DATE, DATE))
    def flight_search(self, event, priority, dpt, to, dep_date, ret_date):
        try:
            flights = self._flight_search(event, dpt, to, dep_date, ret_date)
        except FlightException, e:
            event.addresponse(unicode(e))
            return
        if flights is None:
            return
        if len(flights[0]) == 0:
            event.addresponse(u'No matching departure flights found')
            return
        if len(flights[1]) == 0:
            event.addresponse(u'No matching return flights found')
            return

        cmp = None
        if priority == 'cheapest':
            cmp = lambda a, b: a.int_price() < b.int_price()
        elif priority == 'quickest':
            cmp = lambda a, b: a.int_duration() < b.int_duration()
        if cmp:
            # select best flight based on priority
            for i in xrange(2):
                flights[i].sort(cmp=cmp)
                del flights[i][1:]
        for i, flight_type in zip(xrange(2), ['Departing', 'Returning']):
            if len(flights[i]) > 1:
                event.addresponse(u'%s flights:', flight_type)
            for flight in flights[i][:self.max_results]:
                leading = ''
                if len(flights[i]) == 1:
                    leading = u'%s flight: ' % flight_type
                event.addresponse('%s%s departing %s from %s, arriving %s at %s (flight time %s, %s) costs %s per person',
                        (leading, flight.flight, flight.depart_time, flight.depart_ap, flight.arrive_time,
                            flight.arrive_ap, flight.duration, flight.stops, flight.price or 'unknown'))
        event.addresponse(u'Full results: %s', flights[2])

# vi: set et sta sw=4 ts=4:
