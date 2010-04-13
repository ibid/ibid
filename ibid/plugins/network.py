# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera, Marco Gallotta
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import re
import socket
from ibid.compat import defaultdict
from httplib import HTTPConnection, HTTPSConnection
from os.path import exists
from socket import gethostbyname, gaierror
from subprocess import Popen, PIPE
from sys import version_info
from urllib import getproxies_environment
from urlparse import urlparse

from chardet import detect
try:
    from dns.resolver import Resolver, NoAnswer, NXDOMAIN
    from dns.reversename import from_address
except ImportError:
    Resolver = None

import ibid
from ibid.plugins import Processor, match, authorise
from ibid.config import Option, IntOption, FloatOption, DictOption
from ibid.utils import file_in_path, get_country_codes, get_process_output, \
                       human_join, unicode_output, url_to_bytestring

features = {}

features['dns'] = {
    'description': u'Performs DNS lookups',
    'categories': ('lookup', 'sysadmin',),
}
class DNS(Processor):
    usage = u'dns [<record type>] [for] <host> [from <nameserver>]'

    feature = ('dns',)

    def setup(self):
        if Resolver is None:
            raise Exception("dnspython not installed")

    @match(r'^(?:dns|nslookup|dig|host)'
           r'(?:\s+(a|aaaa|ptr|ns|soa|cname|mx|txt|spf|srv|sshfp|cert))?\s+'
           r'(?:for\s+)?(\S+?)(?:\s+(?:from\s+|@)\s*(\S+))?$')
    def resolve(self, event, record, host, nameserver):
        ipaddr = re.compile(r'\d+\.\d+\.\d+\.\d+')
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

features['ping'] = {
    'description': u'ICMP pings the specified host.',
    'categories': ('sysadmin', 'monitor',),
}
class Ping(Processor):
    usage = u'ping <host>'
    feature = ('ping',)

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
        ping.wait()

        if not error:
            output = unicode_output(output)
            output = u' '.join(output.splitlines()[-2:])
            event.addresponse(output)
        else:
            error = unicode_output(error).replace(u'\n', u' ') \
                                         .replace(u'ping:', u'', 1).strip()
            event.addresponse(u'Error: %s', error)

features['tracepath'] = {
    'description': u'Traces the path to the given host.',
    'categories': ('sysadmin',),
}
class Tracepath(Processor):
    usage = u'tracepath <host>'
    feature = ('tracepath',)

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

features['ipcalc'] = {
    'description': u'IP address calculator',
    'categories': ('sysadmin', 'calculate',),
}
class IPCalc(Processor):
    usage = u"""ipcalc <network>/<subnet>
    ipcalc <address> - <address>"""
    feature = ('ipcalc',)

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

features['http'] = {
    'description': u'Tests if an HTTP site is up and retrieves HTTP URLs.',
    'categories': ('monitor', 'sysadmin',),
}
class HTTP(Processor):
    usage = u"""(get|head) <url>
    is <domain> (up|down)
    tell me when <domain|url> is up"""
    feature = ('http',)
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
                got_title = False
                content_type = self._get_header(headers, 'content-type')
                if (content_type.startswith('text/html') or
                        content_type.startswith('application/xhtml+xml')):
                    match = re.search(r'<title>(.*)<\/title>', data,
                                      re.I | re.DOTALL)
                    if match:
                        got_title = True
                        reply += u' "%s"' % match.groups()[0].strip()

                if not got_title:
                    reply += u' ' + content_type

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
        valid_url = self._makeurl(url)
        if Resolver is not None:
            r = Resolver()
            host = urlparse(valid_url).netloc.split(':')[0]
            try:
                r.query(host)
            except NoAnswer:
                return False, u'No DNS A/CNAME-records for that domain'
            except NXDOMAIN:
                return False, u'No such domain'

        try:
            status, reason, data, headers = self._request(valid_url, 'HEAD')
            # If the URL is only a hostname, we consider 400 series errors to
            # mean up. Full URLs are checked for a sensible response code
            if url == urlparse(url).path and '/' not in url:
                up = status < 500
            else:
                up = status < 400
                reason = u'%(status)d %(reason)s' % {
                    u'status': status,
                    u'reason': reason,
                }
            return up, reason
        except HTTPException:
            return False, u'Server is not responding'

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
        up = self._isitup(url)[0]
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
        ibid.dispatcher.call_later(delay, self._whensitup, event, url, delay,
                                   total_delay)

    @match(r'^(?:tell\s+me|let\s+me\s+know)\s+when\s+(\S+)\s+'
           r'is\s+(?:back\s+)?up$')
    def whensitup(self, event, url):
        up = self._isitup(self._makeurl(url))[0]
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
            try:
                conn.request(method.upper(), url_to_bytestring(url),
                             headers=headers)
                response = conn.getresponse()
                data = response.read(self.max_size)
                conn.close()
            except socket.error, e:
                raise HTTPException(e.message or e.args[1])
        finally:
            if version_info[1] < 6:
                socket.setdefaulttimeout(None)

        contenttype = response.getheader('Content-Type', None)
        if contenttype:
            match = re.search('^charset=([a-zA-Z0-9-]+)', contenttype)
            try:
                if match:
                    data = data.decode(match.group(1))
                elif contenttype.startswith('text/'):
                    data = data.decode('utf-8')
            except UnicodeDecodeError:
                guessed = detect(data)
                if guessed['confidence'] > 0.5:
                    charset = guessed['encoding']
                    # Common guessing mistake:
                    if charset.startswith('ISO-8859') and '\x92' in data:
                        charset = 'windows-1252'
                    data = unicode(data, charset, errors='replace')

        return response.status, response.reason, data, response.getheaders()

features['tld'] = {
    'description': u'Resolve country TLDs (ISO 3166)',
    'categories': ('lookup', 'sysadmin',),
}
class TLD(Processor):
    usage = u""".<tld>
    tld for <country>"""
    feature = ('tld',)

    country_codes = {}

    @match(r'^\.([a-zA-Z]{2})$')
    def tld_to_country(self, event, tld):
        if not self.country_codes:
            self.country_codes = get_country_codes()

        tld = tld.upper()

        if tld in self.country_codes:
            event.addresponse(u'%(tld)s is the ccTLD for %(country)s', {
                'tld': tld,
                'country': self.country_codes[tld],
            })
        else:
            event.addresponse(u"ISO doesn't know about any such ccTLD")

    @match(r'^(?:cc)?tld\s+for\s+(.+)$')
    def country_to_tld(self, event, location):
        if not self.country_codes:
            self.country_codes = get_country_codes()

        output = []
        for tld, country in self.country_codes.iteritems():
            if location.lower() in country.lower():
                output.append(u'%(tld)s is the ccTLD for %(country)s' % {
                    'tld': tld,
                    'country': country,
                })
        if output:
            event.addresponse(human_join(output))
        else:
            event.addresponse(u"ISO doesn't know about any TLD for %s",
                              location)

features['ports'] = {
    'description': u'Looks up port numbers for protocols',
    'categories': ('lookup', 'sysadmin',),
}
class Ports(Processor):
    usage = u"""port for <protocol>
    (tcp|udp) port <number>"""
    feature = ('ports',)
    priority = 10

    services = Option('services', 'Path to services file', '/etc/services')
    nmapservices = Option('nmap-services', "Path to Nmap's services file", '/usr/share/nmap/nmap-services')
    protocols = {}
    ports = {}

    def setup(self):
        self.filename = None
        if exists(self.nmapservices):
            self.filename = self.nmapservices
            self.nmap = True
        elif exists(self.services):
            self.filename = self.services
            self.nmap = False

        if not self.filename:
            raise Exception(u"Services file doesn't exist")

    def _load_services(self):
        if self.protocols:
            return

        self.protocols = defaultdict(list)
        self.ports = defaultdict(list)
        f = open(self.filename)
        for line in f.readlines():
            parts = line.split()
            if parts and not parts[0].startswith('#') and parts[0] != 'unknown':
                number, transport = parts[1].split('/')
                port = '%s (%s)' % (number, transport.upper())
                self.protocols[parts[0].lower()].append(port)
                self.ports[parts[1]].append(parts[0])
                if not self.nmap:
                    for proto in parts[2:]:
                        if proto.startswith('#'):
                            break
                        self.protocols[proto.lower()].append(port)

    @match(r'^(?:(.+)\s+)?ports?(?:\s+numbers?)?(?(1)|\s+for\s+(.+))$')
    def portfor(self, event, proto1, proto2):
        self._load_services()
        protocol = (proto1 or proto2).lower()
        if protocol in self.protocols:
            event.addresponse(human_join(self.protocols[protocol]))
        else:
            event.addresponse(u"I don't know about that protocol")

    @match(r'^(?:(udp|tcp|sctp)\s+)?port\s+(\d+)$')
    def port(self, event, transport, number):
        self._load_services()
        results = []
        if transport:
            results.extend(self.ports.get('%s/%s' % (number, transport.lower()), []))
        else:
            for transport in ('tcp', 'udp', 'sctp'):
                results.extend('%s (%s)' % (protocol, transport.upper()) for protocol in self.ports.get('%s/%s' % (number, transport.lower()), []))

        if results:
            event.addresponse(human_join(results))
        else:
            event.addresponse(u"I don't know about any protocols using that port")

features['nmap'] = {
    'description': u'Finds open network ports on a host or scans a subnet for '
                   u'active hosts.',
    'categories': ('sysadmin',),
}
class Nmap(Processor):
    usage = u"""port scan <hostname>
    net scan <network>/<prefix>"""

    feature = ('nmap',)
    permission = 'nmap'
    min_prefix = IntOption('min_prefix', 'Minimum network prefix that may be scanned', 24)

    def setup(self):
        if not file_in_path('nmap'):
            raise Exception("Cannot locate nmap executable")

    @match(r'^(?:port\s+scan|nmap)\s+([0-9a-z.-]+)$')
    @authorise()
    def host_scan(self, event, host):
        try:
            ip = gethostbyname(host)
        except gaierror, e:
            event.addresponse(unicode(e.args[1]))
            return

        if ip.startswith('127.'):
            event.addresponse(u"I'm not allowed to inspect my host's internal interface.")
            return

        output, error, code = get_process_output(['nmap', '--open', '-n', host])

        ports = []
        gotports = False
        for line in output.splitlines():
            if gotports:
                if not line.split():
                    break
                port, state, service = line.split()
                ports.append('%s (%s)' % (port, service))
            else:
                if line.startswith('Note: Host seems down.'):
                    event.addresponse(u'That host seems to be down')
                    return
                if line.startswith('PORT'):
                    gotports = True

        if ports:
            event.addresponse(human_join(ports))
        else:
            event.addresponse(u'No open ports detected')

    @match(r'^(?:net(?:work)?\s+scan|nmap)\s+((?:[0-9]{1,3}\.){3}[0-9]{1,3})/([0-9]{1,2})$')
    @authorise()
    def net_scan(self, event, network, prefix):
        if int(prefix) < self.min_prefix:
            event.addresponse(u"Sorry, I can't scan networks with a prefix less than %s", self.min_prefix)
            return

        output, error, code = get_process_output(['nmap', '-sP', '-n', '%s/%s' % (network, prefix)])

        hosts = []
        for line in output.splitlines():
            if line.startswith('Host '):
                hosts.append(line.split()[1])

        if hosts:
            event.addresponse(human_join(hosts))
        else:
            event.addresponse(u'No hosts responded to pings')

# vi: set et sta sw=4 ts=4:
