# Copyright (c) 2010, Marco Gallotta
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import re
from urllib2 import HTTPError, URLError

from urllib import urlencode

from ibid.config import Option
from ibid.db import eagerload
from ibid.db.models import Account, Attribute, Identity
from ibid.plugins import Processor, match, auth_responses
from ibid.utils import cacheable_download
from ibid.utils.html import get_html_parse_tree

features = {'usaco': u'Query USACO sections, divisions and more. Since this info is private, users are required to provide their USACO password when linking their USACO account to their ibid account and only linked accounts can be queried. Your password is used only to confirm that the account is yours and is discarded immediately.'}

class UsacoException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __unicode__(self):
        return unicode(self.msg)

class Usaco(Processor):
    """usaco <section|division> for <user>
    usaco <contest> results [for <name|user>]
    (i am|<user> is) <usaco_username> on usaco [password <usaco_password>]"""

    admin_user = Option('admin_user', 'Admin user on USACO', None)
    admin_password = Option('admin_password', 'Admin password on USACO', None)

    feature = 'usaco'
    # Clashes with identity, so lower our priority since if we match, then
    # this is the better match
    priority = -20
    autoload = False

    def _login(self, user, password):
        params = urlencode({'NAME': user.encode('utf-8'), 'PASSWORD': password.encode('utf-8')})
        try:
            etree = get_html_parse_tree(u'http://ace.delos.com/usacogate', data=params, treetype=u'etree')
        except URLError:
            raise UsacoException(u'Sorry, USACO (or my connection?) is down')
        for font in etree.getiterator(u'font'):
            if font.text and u'Please try again' in font.text:
                return None
        return etree

    def _check_login(self, user, password):
        return self._login(user, password) is not None

    def _get_section(self, monitor_url, usaco_user, user):
        try:
            etree = get_html_parse_tree(monitor_url, treetype=u'etree')
        except URLError:
            raise UsacoException(u'Sorry, USACO (or my connection?) is down')
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
        try:
            etree = get_html_parse_tree(monitor_url, treetype=u'etree', data=params)
        except URLError:
            raise UsacoException(u'Sorry, USACO (or my connection?) is down')
        for font in etree.getiterator(u'font'):
            if font.text and u'No STATUS file for' in font.text:
                raise UsacoException(u'Sorry, user %s not found' % user)

    def _get_monitor_url(self):
        if self.admin_user is None or self.admin_password is None:
            raise UsacoException(u'Sorry, you need to configure a USACO admin account')
            return
        try:
            etree = self._login(self.admin_user, self.admin_password)
        except URLError:
            raise UsacoException(u'Sorry, USACO (or my connection?) is down')
        if etree is None:
            raise UsacoException(u'Sorry, the configured USACO admin account is invalid')

        urls = [a.get(u'href') for a in etree.getiterator(u'a')]
        monitor_url = [url for url in urls if u'monitor' in url]
        if len(monitor_url) == 0:
            raise UsacoException(u'USACO admin account does not have teacher status')

        return monitor_url[0]

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
        accounts = event.session.query(Account) \
            .join(['attributes']) \
            .add_entity(Attribute) \
            .filter(Attribute.name == u'usaco_account') \
            .all()

        users = {}
        for a in accounts:
            users[a[1].value] = a[0].username
        return users

    @match(r'^usaco\s+section\s+(?:for\s+)?(.+)$')
    def get_section(self, event, user):
        try:
            usaco_user = self._get_usaco_user(event, user)
            monitor_url = self._get_monitor_url()
            section = self._get_section(monitor_url, usaco_user, user)
        except UsacoException, e:
            event.addresponse(e)
            return

        if section:
            event.addresponse(section)
            return

        try:
            self._add_user(monitor_url, user)
            event.addresponse(self._get_section(monitor_url, usaco_user, user))
        except UsacoException, e:
            event.addresponse(e)
            return

    @match(r'^usaco\s+division\s+(?:for\s+)?(.+)$')
    def get_division(self, event, user):
        try:
            usaco_user = self._get_usaco_user(event, user)
        except UsacoException, e:
            event.addresponse(e)
            return

        params = urlencode({'id': usaco_user.encode('utf-8'), 'search': 'SEARCH'})
        try:
            etree = get_html_parse_tree(u'http://ace.delos.com/showdiv', data=params, treetype=u'etree')
        except URLError:
            event.addresponse(u'Sorry, USACO (or my connection?) is down')
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

    @match(r'^(\S+)\s+(?:is|am)\s+(\S+)\s+on\s+usaco(?:\s+password\s+(\S+))?$')
    def usaco_account(self, event, user, usaco_user, password):
        if password:
            self._redact(event, password)

        if event.public and password:
            event.addresponse(u"Giving your password in public is bad! Please tell me that again in a private message.")
            return

        if not event.account:
            event.addresponse(u'Sorry, you need to create an account with me first (type "usage accounts" to see how)')
            return
        admin = auth_responses(event, u'usacoadmin')
        if user.lower() == 'i':
            if password is None and not admin:
                event.addresponse(u'Sorry, I need your USACO password to verify your account')
            if password and not self._check_login(user, password):
                event.addresponse(u'Sorry, that account is invalid')
                return
            account = event.session.query(Account).get(event.account)
        else:
            if not admin:
                event.addresponse(event.complain)
                return
            account = event.session.query(Account).filter_by(username=user).first()
            if account is None:
                event.addresponse(u"I don't know who %s is", user)
                return

        try:
            monitor_url = self._get_monitor_url()
        except UsacoException, e:
            event.addresponse(e)
            return

        try:
            self._add_user(monitor_url, usaco_user)
        except UsacoException, e:
            event.addresponse(e)
            return

        usaco_account = [attr for attr in account.attributes if attr.name == u'usaco_account']
        if usaco_account:
            usaco_account[0].value = usaco_user
        else:
            account.attributes.append(Attribute('usaco_account', usaco_user))
        event.session.save_or_update(account)
        event.session.commit()

        event.addresponse(u'Done')

    @match(r'^usaco\s+(\S+)\s+results(?:\s+for\s+(.+))?$')
    def usaco_results(self, event, contest, user):
        if user is not None:
            try:
                usaco_user = self._get_usaco_user(event, user)
            except UsacoException, e:
                if 'down' in e.msg:
                    event.addresponse(e)
                    return
                usaco_user = user

        url = u'http://ace.delos.com/%sresults' % contest.upper()
        try:
            filename = cacheable_download(url, u'usaco/results_%s' % contest.upper(), timeout=30)
        except HTTPError:
            event.addresponse(u"Sorry, the results for %s aren't released yet", contest)
        except URLError:
            event.addresponse(u"Sorry, I couldn't fetch the USACO results. Maybe USACO is down?")

        if user is not None:
            users = {usaco_user: user.lower()}
        else:
            try:
                users = self._get_usaco_users(event)
                print users
            except UsacoException, e:
                event.addresponse(e)
                return

        text = open(filename, 'r').read().decode('ISO-8859-2')
        divisions = [u'gold', u'silver', u'bronze']
        results = [[], [], []]
        division = None
        count = 0
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
                match = False
                if usaco_user.lower() in users.keys():
                    match = True
                elif user is not None and name.lower() == user.lower():
                    match = True
                    users[usaco_user] = user
                if match:
                    results[division].append((year, country, name, usaco_user, scores, total))
                    count += 1

        response = []
        for i, division in enumerate(divisions):
            if results[i] and count > 1:
                response.append(u'%s division results:' % division.title())
            for result in results[i]:
                user_string = users[result[3]]
                if users[result[3]] != result[3]:
                    user_string = u'%(user)s (%(usaco_user)s on USACO)' % {
                        u'user': users[result[3]],
                        u'usaco_user': result[3],
                    }
                if count <= 1:
                    division_string = u' in the %s division' % division.title()
                else:
                    division_string = u''
                response.append(u'%(user)s scored %(total)s%(division)s (%(scores)s)' % {
                    u'user': user_string,
                    u'total': result[5],
                    u'scores': result[4],
                    u'division': division_string
                })

        if count == 0:
            if user is not None:
                event.addresponse(u'%(user)s did not compete in %(contest)s', {
                    u'user': user,
                    u'contest': contest,
                })
            else:
                event.addresponse(u"Sorry, I don't know anyone that entered %s", contest)
            return

        event.addresponse(u'\n'.join(response), conflate=False)

# vi: set et sta sw=4 ts=4:
