from math import acos, sin, cos, radians
import logging

from ibid.config import DictOption
from ibid.plugins import Processor, match
from ibid.utils import json_webservice, human_join

log = logging.getLogger('plugins.travel')

help = {}

help['distance'] = u"Returns the distance between two places"
class Distance(Processor):
    u"""distance [in <unit>] between <source> and <destination>
    place search for <placename>"""

    # For Mathematics, see:
    # http://www.mathforum.com/library/drmath/view/51711.html
    # http://mathworld.wolfram.com/GreatCircle.html

    feature = 'distance'

    default_unit_names = {
            'km': "kilometres",
            'mi': "miles",
            'nm': "nautical miles"}
    default_radius_values = {
            'km': 6378,
            'mi': 3963.1,
            'nm': 3443.9}

    unit_names = DictOption('unit_names', 'Names of units in which to specify distances', default_unit_names)
    radius_values = DictOption('radius_values', 'Radius of the earth in the units in which to specify distances', default_radius_values)

    def get_place_data(self, place, num):
        return json_webservice('http://ws.geonames.org/searchJSON', {'q': place, 'maxRows': num})

    def get_place(self, place):
        js = self.get_place_data(place, 1)
        if js['totalResultsCount'] == 0:
            return None
        info = js['geonames'][0]
        return {'name': "%s, %s, %s" % (info['name'], info['adminName1'], info['countryName']),
                'lng': radians(info['lng']),
                'lat': radians(info['lat'])}

    @match(r'^(?:(?:search\s+for\s+place)|(?:place\s+search\s+for)|(?:places\s+for))\s+(\S.+?)\s*$')
    def placesearch(self, event, place):
        js = self.get_place_data(place, 10)
        if js['totalResultsCount'] == 0:
            event.addresponse(u"I don't know of anywhere even remotely like '%s'", place)
        else:
            event.addresponse(u"I can find: %s",
                    (human_join([u"%s, %s, %s" % (p['name'], p['adminName1'], p['countryName'])
                        for p in js['geonames'][:10]],
                        separator=u';')))

    @match(r'^(?:how\s*far|distance)(?:\s+in\s+(\S+))?\s+'
            r'(?:(between)|from)' # Between ... and ... | from ... to ...
            r'\s+(\S.+?)\s+(?(2)and|to)\s+(\S.+?)\s*$')
    def distance(self, event, unit, ignore, src, dst):
        unit_names = self.unit_names
        if unit and unit not in self.unit_names:
            event.addresponse(u"I don't know the unit '%(badunit)s'. I know about: %(knownunits)s", {
                'badunit': unit,
                'knownunits':
                    human_join(u"%s (%s)" % (unit, self.unit_names[unit])
                        for unit in self.unit_names),
            })
            return
        if unit:
            unit_names = [unit]

        srcp, dstp = self.get_place(src), self.get_place(dst)
        if not srcp or not dstp:
            event.addresponse(u"I don't know of anywhere called %s",
                    (u" or ".join("'%s'" % place[0]
                        for place in ((src, srcp), (dst, dstp)) if not place[1])))
            return

        dist = acos(cos(srcp['lng']) * cos(dstp['lng']) * cos(srcp['lat']) * cos(dstp['lat']) +
                    cos(srcp['lat']) * sin(srcp['lng']) * cos(dstp['lat']) * sin(dstp['lng']) +
                    sin(srcp['lat'])*sin(dstp['lat']))

        event.addresponse(u"Approximate distance, as the bot flies, between %(srcname)s and %(dstname)s is: %(distance)s", {
            'srcname': srcp['name'],
            'dstname': dstp['name'],
            'distance': human_join([
                u"%.02f %s" % (self.radius_values[unit]*dist, self.unit_names[unit])
                for unit in unit_names],
                conjunction=u'or'),
        })

# vi: set et sta sw=4 ts=4:
