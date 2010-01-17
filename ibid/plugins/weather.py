from urllib import quote
from urlparse import urljoin
import re
import logging

from ibid.config import DictOption
from ibid.plugins import Processor, match
from ibid.utils import human_join
from ibid.utils.html import get_html_parse_tree

log = logging.getLogger('plugins.weather')

help = {}

help['weather'] = u'Retrieves current weather and forecasts for cities.'
class Weather(Processor):
    u"""weather in <city>
    forecast for <city>"""

    feature = "weather"

    defaults = {    'ct': 'Cape Town, South Africa',
                    'jhb': 'Johannesburg, South Africa',
                    'joburg': 'Johannesburg, South Africa',
               }
    places = DictOption('places', 'Alternate names for places', defaults)
    labels = ('temp', 'humidity', 'dew', 'wind', 'pressure', 'conditions', 'visibility', 'uv', 'clouds', 'ymin', 'ymax', 'ycool', 'sunrise', 'sunset', 'moonrise', 'moonset', 'moonphase', 'metar')
    whitespace = re.compile('\s+')

    class WeatherException(Exception):
        pass

    class TooManyPlacesException(WeatherException):
        pass

    def _text(self, string):
        if not isinstance(string, basestring):
            string = ''.join(string.findAll(text=True))
        return self.whitespace.sub(' ', string).strip()

    def _get_page(self, place):
        if place.lower() in self.places:
            place = self.places[place.lower()]

        soup = get_html_parse_tree('http://m.wund.com/cgi-bin/findweather/getForecast?brand=mobile_metric&query=' + quote(place))

        if soup.body.center and soup.body.center.b.string == 'Search not found:':
            raise Weather.WeatherException(u'City not found')

        if soup.table.tr.th and soup.table.tr.th.string == 'Place: Temperature':
            places = []
            for td in soup.table.findAll('td'):
                places.append(td.find('a', href=re.compile('.*html$')).string)

            # Cities with more than one airport give duplicate entries. We can take the first
            if len([x for x in places if x == places[0]]) == len(places):
                url = urljoin('http://m.wund.com/cgi-bin/findweather/getForecast',
                        soup.table.find('td').find('a', href=re.compile('.*html$'))['href'])
                soup = get_html_parse_tree(url)
            else:
                raise Weather.TooManyPlacesException(places)

        return soup

    def remote_weather(self, place):
        soup = self._get_page(place)
        tds = [x.table for x in soup.findAll('table') if x.table][0].findAll('td')

        # HACK: Some cities include a windchill row, but others don't
        if len(tds) == 39:
            del tds[3]
            del tds[4]

        values = {'place': tds[0].findAll('b')[1].string, 'time': tds[0].findAll('b')[0].string}
        for index, td in enumerate(tds[2::2]):
            values[self.labels[index]] = self._text(td)

        return values

    def remote_forecast(self, place):
        soup = self._get_page(place)
        forecasts = []
        table = [table for table in soup.findAll('table') if table.findAll('td', align='left')][0]

        for td in table.findAll('td', align='left'):
            day = td.b.string
            forecast = u' '.join([self._text(line) for line in td.contents[2:]])
            forecasts.append(u'%s: %s' % (day, self._text(forecast)))

        return forecasts

    @match(r'^weather\s+(?:(?:for|at|in)\s+)?(.+)$')
    def weather(self, event, place):
        try:
            values = self.remote_weather(place)
            event.addresponse(u'In %(place)s at %(time)s: %(temp)s; Humidity: %(humidity)s; Wind: %(wind)s; Conditions: %(conditions)s; Sunrise/set: %(sunrise)s/%(sunset)s; Moonrise/set: %(moonrise)s/%(moonset)s', values)
        except Weather.TooManyPlacesException, e:
            event.addresponse(u'Too many places match %(place)s: %(exception)s', {
                'place': place,
                'exception': human_join(e.args[0], separator=u';'),
            })
        except Weather.WeatherException, e:
            event.addresponse(unicode(e))

    @match(r'^forecast\s+(?:for\s+)?(.+)$')
    def forecast(self, event, place):
        try:
            event.addresponse(u', '.join(self.remote_forecast(place)))
        except Weather.TooManyPlacesException, e:
            event.addresponse(u'Too many places match %(place)s: %(exception)s', {
                'place': place,
                'exception': human_join(e.args[0], separator=u';'),
            })
        except Weather.WeatherException, e:
            event.addresponse(unicode(e))

# vi: set et sta sw=4 ts=4:
