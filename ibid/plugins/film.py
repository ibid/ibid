from urllib2 import urlopen
from urllib import urlencode
from time import strptime, strftime
import logging

from ibid.compat import defaultdict
from ibid.plugins import Processor, match
from ibid.utils import human_join

log = logging.getLogger('plugins.film')

help = {}

help['tvshow'] = u'Retrieves TV show information from tvrage.com.'
class TVShow(Processor):
    u"""tvshow <show>"""

    feature = 'tvshow'

    def remote_tvrage(self, show):
        info_url = 'http://services.tvrage.com/tools/quickinfo.php?%s'

        info = urlopen(info_url % urlencode({'show': show.encode('utf-8')}))

        info = info.read()
        info = info.decode('utf-8')
        if info.startswith('No Show Results Were Found'):
            return
        info = info[5:].splitlines()
        show_info = [i.split('@', 1) for i in info]
        show_dict = dict(show_info)

        #check if there are actual airdates for Latest and Next Episode. None for Next
        #Episode does not neccesarily mean it is nor airing, just the date is unconfirmed.
        show_dict = defaultdict(lambda: 'None', show_info)

        for field in ('Latest Episode', 'Next Episode'):
            if field in show_dict:
                ep, name, date = show_dict[field].split('^', 2)
                count = date.count('/')
                format_from = {
                    0: '%Y',
                    1: '%b/%Y',
                    2: '%b/%d/%Y'
                }[count]
                format_to = ' '.join(('%d', '%B', '%Y')[-1 - count:])
                date = strftime(format_to, strptime(date, format_from))
                show_dict[field] = u'%s - "%s" - %s' % (ep, name, date)

        if 'Genres' in show_dict:
            show_dict['Genres'] = human_join(show_dict['Genres'].split(' | '))

        return show_dict

    @match(r'^tv\s*show\s+(.+)$')
    def tvshow(self, event, show):
        retr_info = self.remote_tvrage(show)

        message = u'Show: %(Show Name)s. Premiered: %(Premiered)s. ' \
                    u'Latest Episode: %(Latest Episode)s. Next Episode: %(Next Episode)s. ' \
                    u'Airtime: %(Airtime)s on %(Network)s. Genres: %(Genres)s. ' \
                    u'Status: %(Status)s. %(Show URL)s'

        if not retr_info:
            event.addresponse(u"I can't find anything out about '%s'", show)
            return

        event.addresponse(message, retr_info)

