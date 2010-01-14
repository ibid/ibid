from xml.etree import ElementTree

from urllib import urlencode

from ibid.config import Option
from ibid.plugins import Processor, match
from ibid.utils.html import get_html_parse_tree

class UsacoException(Exception):
    pass

class Usaco(Processor):
    admin_user = Option('admin_user', 'Admin user on USACO', None)
    admin_password = Option('admin_password', 'Admin password on USACO', None)

    def _get_section(monitor_url, user):
        etree = get_html_parse_tree(monitor_url, treetype=u'etree')
        user = user.lower()
        header = True
        for tr in etree.getiterator(u'tr'):
            if header:
                header = False
                continue
            tds = [t.text for t in tr.getiterator(u'td')]
            print tds[0]
            if tds[0] and tds[0].lower() == user:
                return u'%(name)s is on section %(section)s and last logged in %(days)s ago' % {
                    'name': tds[2],
                    'days': tds[3],
                    'section': tds[5],
                })

        return None

    @match(r'^usaco\s+section\s+(?:for\s+)?(.+)$')
    def get_section(self, event, user):
        if self.admin_user is None or self.admin_password is None:
            event.addresponse(u'Sorry, you need to configure a USACO admin account')
            return
        params = urlencode({u'NAME': self.admin_user, u'PASSWORD': self.admin_password})
        etree = get_html_parse_tree(u'http://ace.delos.com/usacogate', data=params, treetype=u'etree')

        #TODO handle invalid login

        urls = [a.get(u'href') for a in etree.getiterator(u'a')]
        monitor_url = [url for url in urls if u'monitor' in url][0]
        if len(monitor_url) == 0:
            event.addresponse(u'USACO admin account does not have teacher status')
            return

        section = self._get_section(monitor_url, user)
        if section:
            event.addresponse(section)
            return

# vi: set et sta sw=4 ts=4:
