# Copyright (c) 2010, Marco Gallotta
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import re
from urllib2 import HTTPError

from urllib import urlencode

from ibid.config import Option
from ibid.db import eagerload
from ibid.db.models import Account, Attribute, Identity
from ibid.plugins import Processor, match
from ibid.utils import cacheable_download
from ibid.utils.html import get_html_parse_tree

help = {u'usaco': u'Query USACO sections, divisions and more. Since this info is private, users are required to provide their USACO password when linking their USACO account to their ibid account and only linked accounts can be queried. Your password is used only to confirm that the account is yours and is discarded immediately.'}

class UsacoException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __unicode__(self):
        return unicode(self.msg)

class Usaco(Processor):
    """usaco <section|division> for <user>
    usaco <contest> results [for <user>]
    i am <usaco_username> on usaco password <usaco_password>"""

    admin_user = Option('admin_user', 'Admin user on USACO', None)
    admin_password = Option('admin_password', 'Admin password on USACO', None)

    feature = 'usaco'
    # Clashes with identity, so lower our priority since if we match, then
    # this is the better match
    priority = -20
    autoload = False

    def _login(self, user, password):
        params = urlencode({'NAME': user.encode('utf-8'), 'PASSWORD': password.encode('utf-8')})
        etree = get_html_parse_tree(u'http://ace.delos.com/usacogate', data=params, treetype=u'etree')
        for font in etree.getiterator(u'font'):
            if font.text and u'Please try again' in font.text:
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
        params = urlencode({'STUDENTID': user.encode('utf-8'), 'ADD': 'ADD STUDENT',
            'a': auth.encode('utf-8'), 'monitor': '1'})
        etree = get_html_parse_tree(monitor_url, treetype=u'etree', data=params)
        for font in etree.getiterator(u'font'):
            if font.text and u'No STATUS file for' in font.text:
                raise UsacoException(u'Sorry, user %s not found' % user)

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
            .options(eagerload('attributes')) \
            .filter(Account.username == user) \
            .first()
        if account is None:
            account = event.session.query(Account) \
                .options(eagerload('attributes')) \
                .join('identities') \
                .filter(Identity.identity == user) \
                .filter(Identity.source == event.source) \
                .first()
            if account is None:
                raise UsacoException(u'Sorry, %s has not been linked to a USACO account yet' % user)

        usaco_account = [attr.value for attr in account.attributes if attr.name == 'usaco_account']
        if len(usaco_account) == 0:
            raise UsacoException(u'Sorry, %s has not been linked to a USACO account yet' % user)
        return usaco_account[0]

    def _get_usaco_users(self, event):
        accounts = event.session.query(Identity) \
            .join(['account', 'attributes']) \
            .add_entity(Attribute) \
            .filter(Attribute.name == u'usaco_account') \
            .filter(Identity.source == event.source) \
            .all()

        users = {}
        for a in accounts:
            users[a[1].value] = a[0].identity
        return users

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

        params = urlencode({'id': usaco_user.encode('utf-8'), 'search': 'SEARCH'})
        etree = get_html_parse_tree(u'http://ace.delos.com/showdiv', data=params, treetype=u'etree')
        division = [b.text for b in etree.getiterator(u'b') if b.text and usaco_user in b.text][0]
        if division.find(u'would compete') != -1:
            event.addresponse(u'%(user)s (%(usaco_user)s on USACO) has not competed in a USACO before',
                    {u'user': user, u'usaco_user': usaco_user})
        matches = re.search(r'(\w+) Division', division)
        division = matches.group(1).lower()
        event.addresponse(u'%(user)s (%(usaco_user)s on USACO) is in the %(division)s division',
                {u'user': user, u'usaco_user': usaco_user, u'division': division})

    def _redact(self, event, term):
        for type in ['raw', 'deaddressed', 'clean', 'stripped']:
            event['message'][type] = re.sub(r'(.*)(%s)' % re.escape(term), r'\1[redacted]', event['message'][type])

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
        usaco_account = [attr for attr in account.attributes if attr.name == u'usaco_account']
        if usaco_account:
            usaco_account[0].value = user
        else:
            account.attributes.append(Attribute('usaco_account', user))
        event.session.save_or_update(account)
        event.session.commit()

        event.addresponse(u'Done')

    @match(r'^usaco\s+(\S+)\s+results(?:\s+for\s+(\S+))?$')
    def usaco_results(self, event, contest, user):
        if user is not None:
            try:
                usaco_user = self._get_usaco_user(event, user)
            except UsacoException, e:
                event.addresponse(e)
                return

        url = u'http://ace.delos.com/%sresults' % contest.upper()
        try:
            filename = cacheable_download(url, u'usaco/results_%s' % contest.upper())
        except HTTPError:
            event.addresponse(u"Sorry, the results for %s aren't released yet", contest)

        if user is not None:
            users = {usaco_user: user}
        else:
            users = self._get_usaco_users(event)

        text = open(filename, 'r').read().decode('ISO-8859-2')
        divisions = [u'gold', u'silver', u'bronze']
        results = [[], [], []]
        division = None
        for line in text.splitlines():
            for index, d in enumerate(divisions):
                if d in line.lower():
                    division = index
            # Example results line:
            #            2010 POL Jakub Pachocki      meret1      ***** ***** 270 ***** ***** * 396 ***** ***** ** 324 1000
            matches = re.match(r'^\s*(\d{4})\s+([A-Z]{3})\s+(.+?)\s+(\S+\d)\s+([\*xts\.e0-9 ]+?)\s+(\d+)\s*$', line)
            if matches:
                year = matches.group(1)
                country = matches.group(2)
                name = matches.group(3)
                usaco_user = matches.group(4)
                scores = matches.group(5)
                total = matches.group(6)
                if usaco_user in users.keys():
                    results[division].append((year, country, name, usaco_user, scores, total))

        response = []
        for i, division in enumerate(divisions):
            if results[i]:
                response.append(u'%s division results:' % division.title())
            for result in results[i]:
                response.append(u'%(user)s (%(usaco_user)s on USACO) scored %(total)s (%(scores)s)' % {
                    u'user': users[result[3]],
                    u'usaco_user': result[3],
                    u'total': result[5],
                    u'scores': result[4],
                })
        event.addresponse(u'\n'.join(response), conflate=False)

# vi: set et sta sw=4 ts=4:
