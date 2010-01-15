import re
from xml.etree import ElementTree

from urllib import urlencode

import ibid
from ibid.config import Option
from ibid.db import eagerload, and_
from ibid.db.models import Account, Attribute, Identity
from ibid.plugins import Processor, match
from ibid.utils.html import get_html_parse_tree

class UsacoException(Exception):
    pass

class Usaco(Processor):
    admin_user = Option('admin_user', 'Admin user on USACO', None)
    admin_password = Option('admin_password', 'Admin password on USACO', None)

    priority = -20

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

    def _get_monitor_url(self):
        if self.admin_user is None or self.admin_password is None:
            raise UsacoException(u'Sorry, you need to configure a USACO admin account')
            return
        etree = self._login(self.admin_user, self.admin_password)
        if etree is None:
            raise UsacoException(u'Sorry, the configured USACO admin account is invalid')

        urls = [a.get(u'href') for a in etree.getiterator(u'a')]
        monitor_url = [url for url in urls if u'monitor' in url][0]
        if len(monitor_url) == 0:
            raise UsacoException(u'USACO admin account does not have teacher status')

        return monitor_url

    def _get_usaco_user(self, event, user):
        account = event.session.query(Account) \
            .filter(Account.username == user) \
            .first()
        if account is None:
            account = event.session.query(Account) \
                .options(eagerload('identities')) \
                .join(Identity) \
                .filter(and_(
                    Identity.identity == user,
                    Identity.source == event.source)) \
                .first()
            if account is None:
                return

        usaco_account = [attr.value for attr in account.attributes if attr.name == 'usaco_account']
        if len(usaco_account) == 0:
            raise UsacoException(u'Sorry, %s has been linked to a USACO account yet' % user)
        return usaco_account[0]

    @match(r'^usaco\s+section\s+(?:for\s+)?(.+)$')
    def get_section(self, event, user):
        try:
            usaco_user = self._get_usaco_user(event, user)
            monitor_url = self._get_monitor_url()
        except UsacoException, e:
            event.addresponse(e)
            return

        section = self._get_section(monitor_url, usaco_user)
        if section:
            event.addresponse(section)
            return

        try:
            self._add_user(monitor_url, user)
        except UsacoException, e:
            event.addresponse(e)
            return

        event.addresponse(self._get_section(monitor_url, user))

    @match(r'^i\s+am\s+(\S+)\s+on\s+usaco\s+password\s+(\S+)$')
    def usaco_account(self, event, user, password):
        # TODO strip password from event
        if not self._check_login(user, password):
            event.addresponse(u'Sorry, that account is invalid')
            return
        if not event.account:
            event.addresponse(u'Sorry, you need to create an account first')
            return

        try:
            monitor_url = self._get_monitor_url()
        except UsacoException, e:
            event.addresponse(e)
            return

        # TODO handle user not existing
        self._add_user(monitor_url, user)

        account = event.session.query(Account).get(event.account)
        account.attributes.append(Attribute('usaco_account', user))
        event.addresponse(u'Done')

# vi: set et sta sw=4 ts=4:
