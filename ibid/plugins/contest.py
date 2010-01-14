import re
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

    def _login(self, user, password):
        params = urlencode({u'NAME': user, u'PASSWORD': password})
        etree = get_html_parse_tree(u'http://ace.delos.com/usacogate', data=params, treetype=u'etree')
        for font in etree.getiterator(u'font'):
            if font.text and font.text.find('Please try again') != -1:
                return None
        return etree

    def _check_login(self, user, password):
        return self._login(user, password) is not None

    def _get_section(self, monitor_url, user):
        etree = get_html_parse_tree(monitor_url, treetype=u'etree')
        user = user.lower()
        header = True
        for tr in etree.getiterator(u'tr'):
            if header:
                header = False
                continue
            tds = [t.text for t in tr.getiterator(u'td')]
            if tds[0] and tds[0].lower() == user:
                return u'%(name)s is on section %(section)s and last logged in %(days)s ago' % {
                    'name': tds[2],
                    'days': tds[3],
                    'section': tds[5],
                }

        return None

    def _add_user(self, monitor_url, user):
        matches = re.search(r'a=(.+)&', monitor_url)
        auth = matches.group(1)
        params = urlencode({u'STUDENTID': user, 'ADD': 'ADD STUDENT',
            u'a': auth, u'monitor': u'1'})
        etree = get_html_parse_tree(monitor_url, treetype=u'etree', data=params)

    @match(r'^usaco\s+section\s+(?:for\s+)?(.+)$')
    def get_section(self, event, user):
        if self.admin_user is None or self.admin_password is None:
            event.addresponse(u'Sorry, you need to configure a USACO admin account')
            return
        etree = self._login(self.admin_user, self.admin_password)
        if etree is None:
            event.addresponse(u'Sorry, the configured USACO admin account is invalid')

        urls = [a.get(u'href') for a in etree.getiterator(u'a')]
        monitor_url = [url for url in urls if u'monitor' in url][0]
        if len(monitor_url) == 0:
            event.addresponse(u'USACO admin account does not have teacher status')
            return

        section = self._get_section(monitor_url, user)
        if section:
            event.addresponse(section)
            return

        try:
            self._add_user(monitor_url, user)
        except UsacoException, e:
            event.addresponse(e.msg)
            return

        event.addresponse(self._get_section(monitor_url, user))

# vi: set et sta sw=4 ts=4:
