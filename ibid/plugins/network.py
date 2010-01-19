# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera, Marco Gallotta
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import re
import socket
from httplib import HTTPConnection, HTTPSConnection
from subprocess import Popen, PIPE
from urllib import getproxies_environment
from urlparse import urlparse
from sys import version_info

try:
    from dns.resolver import Resolver, NoAnswer, NXDOMAIN
    from dns.reversename import from_address
except ImportError:
    Resolver = NoAnswer = NXDOMAIN = from_address = None

import ibid
from ibid.plugins import Processor, match
from ibid.config import Option, IntOption, FloatOption, DictOption
from ibid.utils import file_in_path, unicode_output, human_join, \
                       url_to_bytestring
from ibid.utils.html import get_country_codes

help = {}
ipaddr = re.compile('\d+\.\d+\.\d+\.\d+')
title = re.compile(r'<title>(.*)<\/title>', re.I+re.S)

help['dns'] = u'Performs DNS lookups'
class DNS(Processor):
    u"""dns [<record type>] [for] <host> [from <nameserver>]"""

    feature = 'dns'

    def setup(self):
        if Resolver is None:
            raise Exception("dnspython not installed")

    @match(r'^(?:dns|nslookup|dig|host)'
           r'(?:\s+(a|aaaa|ptr|ns|soa|cname|mx|txt|spf|srv|sshfp|cert))?\s+'
           r'(?:for\s+)?(\S+?)(?:\s+(?:from\s+|@)\s*(\S+))?$')
    def resolve(self, event, record, host, nameserver):
        if not record:
            if ipaddr.search(host):
                host = from_address(host)
                record = 'PTR'
            else:
                record = 'A'

        resolver = Resolver()
        if nameserver:
            if not ipaddr.search(nameserver):
                nameserver = resolver.query(nameserver, 'A')[0].address
            resolver.nameservers = [nameserver]

        try:
            answers = resolver.query(host, str(record))
        except NoAnswer:
            event.addresponse(
                u"I couldn't find any %(type)s records for %(host)s", {
                    'type': record,
                    'host': host,
                })
            return
        except NXDOMAIN:
            event.addresponse(u"I couldn't find the domain %s", host)
            return

        responses = []
        for rdata in answers:
            responses.append(unicode(rdata))

        event.addresponse(u'Records: %s', human_join(responses))

help['ping'] = u'ICMP pings the specified host.'
class Ping(Processor):
    u"""ping <host>"""
    feature = 'ping'

    ping = Option('ping', 'Path to ping executable', 'ping')

    def setup(self):
        if not file_in_path(self.ping):
            raise Exception("Cannot locate ping executable")

    @match(r'^ping\s+(\S+)$')
    def handle_ping(self, event, host):
        if host.strip().startswith("-"):
            event.addresponse(False)
            return

        ping = Popen([self.ping, '-q', '-c5', host], stdout=PIPE, stderr=PIPE)
        output, error = ping.communicate()
        code = ping.wait()

        if code == 0:
            output = unicode_output(output)
            output = u' '.join(output.splitlines()[-2:])
            event.addresponse(output)
        else:
            error = unicode_output(error).replace(u'\n', u' ') \
                                         .replace(u'ping:', u'', 1).strip()
            event.addresponse(u'Error: %s', error)

help['tracepath'] = u'Traces the path to the given host.'
class Tracepath(Processor):
    u"""tracepath <host>"""
    feature = 'tracepath'

    tracepath = Option('tracepath', 'Path to tracepath executable', 'tracepath')

    def setup(self):
        if not file_in_path(self.tracepath):
            raise Exception("Cannot locate tracepath executable")

    @match(r'^tracepath\s+(\S+)$')
    def handle_tracepath(self, event, host):

        tracepath = Popen([self.tracepath, host], stdout=PIPE, stderr=PIPE)
        output, error = tracepath.communicate()
        code = tracepath.wait()

        if code == 0:
            output = unicode_output(output)
            event.addresponse(output, conflate=False)
        else:
            error = unicode_output(error.strip())
            event.addresponse(u'Error: %s', error.replace(u'\n', u' '))

help['ipcalc'] = u'IP address calculator'
class IPCalc(Processor):
    u"""ipcalc <network>/<subnet>
    ipcalc <address> - <address>"""
    feature = 'ipcalc'

    ipcalc = Option('ipcalc', 'Path to ipcalc executable', 'ipcalc')

    def setup(self):
        if not file_in_path(self.ipcalc):
            raise Exception("Cannot locate ipcalc executable")

    def call_ipcalc(self, parameters):
        ipcalc = Popen([self.ipcalc, '-n', '-b'] + parameters,
                       stdout=PIPE, stderr=PIPE)
        output, error = ipcalc.communicate()
        code = ipcalc.wait()
        output = unicode_output(output)

        return (code, output, error)

    @match(r'^ipcalc\s+((?:\d{1,3}\.){3}\d{1,3}|(?:0x)?[0-9A-F]{8})'
           r'(?:(?:/|\s+)((?:\d{1,3}\.){3}\d{1,3}|\d{1,2}))?$')
    def ipcalc_netmask(self, event, address, netmask):
        address = address
        if netmask:
            address += u'/' + netmask
        code, output, error = self.call_ipcalc([address])

        if code == 0:
            if output.startswith(u'INVALID ADDRESS'):
                event.addresponse(u"That's an invalid address. "
                                  u"Try something like 192.168.1.0/24")
            else:
                response = {}
                for line in output.splitlines():
                    if ":" in line:
                        name, value = [x.strip() for x in line.split(u':', 1)]
                        name = name.lower()
                        if name == "netmask":
                            value, response['cidr'] = value.split(' = ')
                        elif name == "hosts/net":
                            value, response['class'] = value.split(None, 1)
                        response[name] = value

                event.addresponse(u'Host: %(address)s/%(netmask)s (/%(cidr)s) '
                    u'Wildcard: %(wildcard)s | '
                    u'Network: %(network)s (%(hostmin)s - %(hostmax)s) '
                    u'Broadcast: %(broadcast)s Hosts: %(hosts/net)s %(class)s',
                    response)
        else:
            error = unicode_output(error.strip())
            event.addresponse(error.replace(u'\n', u' '))

    @match(r'^ipcalc\s+((?:\d{1,3}\.){3}\d{1,3}|(?:0x)?[0-9A-F]{8})\s*-\s*'
           r'((?:\d{1,3}\.){3}\d{1,3}|(?:0x)?[0-9A-F]{8})$')
    def ipcalc_deggregate(self, event, frm, to):
        code, output, error = self.call_ipcalc([frm, '-', to])

        if code == 0:
            if output.startswith(u'INVALID ADDRESS'):
                event.addresponse(u"That's an invalid address. "
                                  u"Try something like 192.168.1.0")
            else:
                event.addresponse(u'Deaggregates to: %s',
                                  human_join(output.splitlines()[1:]))
        else:
            error = unicode_output(error.strip())
            event.addresponse(error.replace(u'\n', u' '))

class HTTPException(Exception):
    pass

help['http'] = u'Tests if an HTTP site is up and retrieves HTTP URLs.'
class HTTP(Processor):
    u"""(get|head) <url>
    is <domain> (up|down)
    tell me when <domain|url> is up"""
    feature = 'http'
    priority = -10

    max_size = IntOption('max_size', u'Only request this many bytes', 500)
    timeout = IntOption('timeout',
            u'Timeout for HTTP connections in seconds', 15)
    sites = DictOption('sites', u'Mapping of site names to domains', {})
    max_hops = IntOption('max_hops',
            u'Maximum hops in get/head when receiving a 30[12]', 3)
    whensitup_delay = IntOption('whensitup_delay',
            u'Initial delay between whensitup attempts in seconds', 60)
    whensitup_factor = FloatOption('whensitup_factor',
            u'Factor to mutliply subsequent delays by for whensitup', 1.03)
    whensitup_maxdelay = IntOption('whensitup_maxdelay',
            u'Maximum delay between whensitup attempts in seconds', 30*60)
    whensitup_maxperiod = FloatOption('whensitup_maxperiod',
            u'Maximum period after which to stop checking the url '
            u'for whensitup in hours', 72)

    def _get_header(self, headers, name):
        for header in headers:
            if header[0] == name:
                return header[1]
        return None

    @match(r'^(get|head)\s+(\S+)$')
    def get(self, event, action, url):
        try:
            status, reason, data, headers = self._request(self._makeurl(url),
                                                          action.upper())
            reply = u'%s %s' % (status, reason)

            hops = 0
            while status in (301, 302) and self._get_header(headers,
                                                            'location'):
                location = self._get_header(headers, 'location')
                status, reason, data, headers = self._request(location, 'GET')
                if hops >= self.max_hops:
                    reply += u' to %s' % location
                    break
                hops += 1
                reply += u' to %(location)s, which gets a ' \
                         u'%(status)d %(reason)s' % {
                    u'location': location,
                    u'status': status,
                    u'reason': reason,
                }

            if action.upper() == 'GET':
                match = title.search(data)
                print data
                if match:
                    reply += u' "%s"' % match.groups()[0].strip()

            event.addresponse(reply)

        except HTTPException, e:
            event.addresponse(unicode(e))

    def _makeurl(self, url):
        if url in self.sites:
            url = self.sites[url]
        else:
            if not urlparse(url).netloc:
                if '.' not in url:
                    url += '.com'
                url = 'http://' + url
            if not urlparse(url).path:
                url += '/'
        return url

    def _isitup(self, url):
        try:
            status, reason, data, headers = self._request(self._makeurl(url),
                                                          'HEAD')
            if not urlparse(url).netloc and not urlparse('http://' + url).path:
                up = True # only domain provided: any response = Up
            else:
                up = status < 400 # url provided: check http status
                reason = u'%(status)d %(reason)s' % {
                    u'status': status,
                    u'reason': reason,
                }
        except HTTPException:
            up = False
            reason = u'Server is not responding'

        return up, reason

    @match(r'^is\s+(\S+)\s+(up|down)$')
    def isit(self, event, url, type):
        up, reason = self._isitup(url)
        if up:
            if type.lower() == 'up':
                event.addresponse(u'Yes, %s is up', url)
            else:
                event.addresponse(u"No, it's just you")
        else:
            if type.lower() == 'up':
                event.addresponse(u'No, %(url)s is down (%(reason)s)', {
                    u'url': url,
                    u'reason': reason,
                })
            else:
                event.addresponse(u'Yes, %(url)s is down (%(reason)s)', {
                    u'url': url,
                    u'reason': reason,
                })

    def _whensitup(self, event, url, delay, total_delay = 0):
        up, _ = self._isitup(url)
        if up:
            event.addresponse(u'%s is now up', self._makeurl(url))
            return
        total_delay += delay
        if total_delay >= self.whensitup_maxperiod * 60 * 60:
            event.addresponse(u"Sorry, it appears %s is never coming up. "
                              u"I'm not going to check any more.",
                              self._makeurl(url))
        delay *= self.whensitup_factor
        delay = max(delay, self.whensitup_maxdelay)
        ibid.dispatcher.call_later(delay, self._whensitup, event, url, delay)

    @match(r'^(?:tell\s+me|let\s+me\s+know)\s+when\s+(\S+)\s+'
           r'is\s+(?:back\s+)?up$')
    def whensitup(self, event, url):
        up, _ = self._isitup(self._makeurl(url))
        if up:
            event.addresponse(u'%s is up right now', self._makeurl(url))
            return
        ibid.dispatcher.call_later(self.whensitup_delay, self._whensitup,
                                   event, url, self.whensitup_delay)
        event.addresponse(u"I'll let you know when %s is up", url)

    def _request(self, url, method):
        scheme, host = urlparse(url)[:2]
        scheme = scheme.lower()
        proxies = getproxies_environment()
        if scheme in proxies:
            scheme, host = urlparse(proxies[scheme])[:2]
            scheme = scheme.lower()

        kwargs = {}
        if version_info[1] >= 6:
            kwargs['timeout'] = self.timeout
        else:
            socket.setdefaulttimeout(self.timeout)

        if scheme == "https":
            conn = HTTPSConnection(host, **kwargs)
        else:
            conn = HTTPConnection(host, **kwargs)

        headers={}
        if method == 'GET':
            headers['Range'] = 'bytes=0-%s' % self.max_size

        try:
            conn.request(method.upper(), url_to_bytestring(url),
                         headers=headers)
            response = conn.getresponse()
            data = response.read(self.max_size)
            conn.close()
        except socket.error, e:
            raise HTTPException(e.message or e.args[1])

        contenttype = response.getheader('Content-Type',
                                         'text/html; charset=utf-8')
        match = re.search('charset=([a-zA-Z0-9-]+)', contenttype)
        charset = match and match.group(1) or 'utf-8'

        return response.status, response.reason, data.decode(charset), \
               response.getheaders()

help['tld'] = u"Resolve country TLDs (ISO 3166)"
class TLD(Processor):
    u""".<tld>
    tld for <country>"""
    feature = 'tld'

    country_codes = {}

    @match(r'^\.([a-zA-Z]{2})$')
    def tld_to_country(self, event, tld):
        if not self.country_codes:
            self.country_codes = get_country_codes()

        tld = tld.upper()

        if tld in self.country_codes:
            event.addresponse(u'%(tld)s is the TLD for %(country)s', {
                'tld': tld,
                'country': self.country_codes[tld],
            })
        else:
            event.addresponse(u"ISO doesn't know about any such TLD")

    @match(r'^tld\s+for\s+(.+)$')
    def country_to_tld(self, event, location):
        if not self.country_codes:
            self.country_codes = get_country_codes()

        for tld, country in self.country_codes.iteritems():
            if location.lower() in country.lower():
                event.addresponse(u'%(tld)s is the TLD for %(country)s', {
                    'tld': tld,
                    'country': country,
                })
                return

        event.addresponse(u"ISO doesn't know about any TLD for %s", location)

# vi: set et sta sw=4 ts=4:
