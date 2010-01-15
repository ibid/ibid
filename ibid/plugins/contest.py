import re
from xml.etree import ElementTree

from urllib import urlencode

import ibid
from ibid.config import Option
from ibid.db import eagerload, and_
from ibid.db.models import Account, Attribute, Identity
from ibid.plugins import Processor, match
from ibid.utils.html import get_html_parse_tree

help = {u'usaco': u'Query USACO sections, divisions and more. Since this info is private, users are required to provide their USACO password when linking their USACO account to their ibid account and only linked accounts can be queried. Please note that your password is used only to confirm that the account is yours and is discarded immediately.'}

class UsacoException(Exception):
    pass

class Usaco(Processor):
    """usaco <section|division> for <user>
    i am <usaco_username> on usaco password <usaco_password>"""

    admin_user = Option('admin_user', 'Admin user on USACO', None)
    admin_password = Option('admin_password', 'Admin password on USACO', None)

    feature = 'usaco'
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

    def _get_section(self, monitor_url, usaco_user, user):
        etree = get_html_parse_tree(monitor_url, treetype=u'etree')
        usaco_user = usaco_user.lower()
        header = True
        for tr in etree.getiterator(u'tr'):
            if header:
                header = False
                continue
            tds = [t.text for t in tr.getiterator(u'td')]
            section = u'is on section %s' % tds[5]
            if tds[5] == u'DONE':
                section = u'has completed USACO training'
            if tds[0] and tds[0].lower() == usaco_user:
                return u'%(user)s (%(usaco_user)s on USACO) %(section)s and last logged in %(days)s ago' % {
                    'user': user,
                    'usaco_user': usaco_user,
                    'days': tds[3],
                    'section': section,
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
                .join('identities') \
                .filter(and_(
                    Identity.identity == user,
                    Identity.source == event.source)) \
                .first()
            if account is None:
                raise UsacoException(u'Sorry, %s has not been linked to a USACO account yet' % user)

        usaco_account = [attr.value for attr in account.attributes if attr.name == 'usaco_account']
        if len(usaco_account) == 0:
            raise UsacoException(u'Sorry, %s has not been linked to a USACO account yet' % user)
        return usaco_account[0]

    @match(r'^usaco\s+section\s+(?:for\s+)?(.+)$')
    def get_section(self, event, user):
        try:
            usaco_user = self._get_usaco_user(event, user)
            monitor_url = self._get_monitor_url()
        except UsacoException, e:
            event.addresponse(e)
            return

        section = self._get_section(monitor_url, usaco_user, user)
        if section:
            event.addresponse(section)
            return

        try:
            self._add_user(monitor_url, user)
        except UsacoException, e:
            event.addresponse(e)
            return

        event.addresponse(self._get_section(monitor_url, usaco_user, user))

    @match(r'^usaco\s+division\s+(?:for\s+)?(.+)$')
    def get_division(self, event, user):
        try:
            usaco_user = self._get_usaco_user(event, user)
        except UsacoException, e:
            event.addresponse(e)
            return

        params = urlencode({u'id': usaco_user, u'search': u'SEARCH'})
        etree = get_html_parse_tree(u'http://ace.delos.com/showdiv', data=params, treetype=u'etree')
        division = [b.text for b in etree.getiterator(u'b') if b.text and b.text.find(usaco_user) != -1][0]
        if division.find(u'would compete') != -1:
            event.addresponse(u'%(user)s (%(usaco_user)s on USACO) has not competed in a USACO before',
                    {u'user': user, u'usaco_user': usaco_user})
        matches = re.search(r'(\w+) Division', division)
        division = matches.group(1).lower()
        event.addresponse(u'%(user)s (%(usaco_user)s on USACO) is in the %(division)s division',
                {u'user': user, u'usaco_user': usaco_user, u'division': division})

    def _redact(self, event, term):
        for type in ['raw', 'deaddressed', 'clean', 'stripped']:
            # TODO find better way: usually we only want one specific instance of
            # term redacted if there are multiple occurences
            event['message'][type] = event['message'][type].replace(term, u'__redacted__')

    @match(r'^i\s+am\s+(\S+)\s+on\s+usaco\s+password\s+(\S+)$')
    def usaco_account(self, event, user, password):
        self._redact(event, password)

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

        self._add_user(monitor_url, user)

        account = event.session.query(Account).get(event.account)
        account.attributes.append(Attribute('usaco_account', user))
        event.addresponse(u'Done')

# vi: set et sta sw=4 ts=4:
