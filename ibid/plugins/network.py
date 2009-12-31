import re
from httplib import HTTPConnection, HTTPSConnection
from subprocess import Popen, PIPE
from urllib import getproxies_environment
from urlparse import urlparse, urljoin

from dns.resolver import Resolver, NoAnswer, NXDOMAIN
from dns.reversename import from_address

from ibid.plugins import Processor, match
from ibid.config import Option, IntOption
from ibid.utils import file_in_path, unicode_output, human_join

help = {}
ipaddr = re.compile('\d+\.\d+\.\d+\.\d+')

help['dns'] = u'Performs DNS lookups'
class DNS(Processor):
    u"""dns [<record type>] [for] <host> [from <nameserver>]"""

    feature = 'dns'

    @match(r'^(?:dns|nslookup|dig|host)(?:\s+(a|aaaa|ptr|ns|soa|cname|mx|txt|spf|srv|sshfp|cert))?\s+(?:for\s+)?(\S+?)(?:\s+(?:from\s+|@)\s*(\S+))?$')
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
            event.addresponse(u"I couldn't find any %(type)s records for %(host)s", {
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
            error = unicode_output(error).replace(u'\n', u' ').replace(u'ping:', u'', 1).strip()
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
        ipcalc = Popen([self.ipcalc, '-n', '-b'] + parameters, stdout=PIPE, stderr=PIPE)
        output, error = ipcalc.communicate()
        code = ipcalc.wait()
        output = unicode_output(output)

        return (code, output, error)

    @match(r'^ipcalc\s+((?:\d{1,3}\.){3}\d{1,3}|(?:0x)?[0-9A-F]{8})(?:(?:/|\s+)((?:\d{1,3}\.){3}\d{1,3}|\d{1,2}))?$')
    def ipcalc_netmask(self, event, address, netmask):
        address = address
        if netmask:
            address += u'/' + netmask
        code, output, error = self.call_ipcalc([address])

        if code == 0:
            if output.startswith(u'INVALID ADDRESS'):
                event.addresponse(u"That's an invalid address. Try something like 192.168.1.0/24")
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

                event.addresponse(u'Host: %(address)s/%(netmask)s (/%(cidr)s) Wildcard: %(wildcard)s | '
                    u'Network: %(network)s (%(hostmin)s - %(hostmax)s) Broadcast: %(broadcast)s Hosts: %(hosts/net)s %(class)s',
                    response)
        else:
            error = unicode_output(error.strip())
            event.addresponse(error.replace(u'\n', u' '))

    @match(r'^ipcalc\s+((?:\d{1,3}\.){3}\d{1,3}|(?:0x)?[0-9A-F]{8})\s*-\s*((?:\d{1,3}\.){3}\d{1,3}|(?:0x)?[0-9A-F]{8})$')
    def ipcalc_deggregate(self, event, frm, to):
        code, output, error = self.call_ipcalc([frm, '-', to])

        if code == 0:
            if output.startswith(u'INVALID ADDRESS'):
                event.addresponse(u"That's an invalid address. Try something like 192.168.1.0")
            else:
                event.addresponse(u'Deaggregates to: %s', human_join(output.splitlines()[1:]))
        else:
            error = unicode_output(error.strip())
            event.addresponse(error.replace(u'\n', u' '))

title = re.compile(r'<title>(.*)<\/title>', re.I+re.S)

help['get'] = u'Retrieves a URL and returns the HTTP status and optionally the HTML title.'
class HTTP(Processor):
    u"""(get|head) <url>"""
    feature = 'get'

    max_size = IntOption('max_size', 'Only request this many bytes', 500)

    @match(r'^(get|head)\s+(\S+\.\S+)$')
    def get(self, event, action, url):
        url = urljoin('http://', url)
        status, reason, data = self._request(url, action.upper())
        reply = u'%s %s' % (status, reason)

        if action.upper() == 'GET':
            match = title.search(data)
            if match:
                reply += u' "%s"' % match.groups()[0].strip()

        event.addresponse(reply)

    @match(r'^is\s+(\S+)\s+(up|down)$')
    def isit(self, event, site, type):
        if '.' not in site:
            site = site + '.com'
        url = urljoin('http://', site)
        status, reason, data = self._request(url, 'HEAD')

        if status < 400 and type.lower() == 'up':
            event.addresponse(u'%s is up', (site,))
        else:
            event.addresponse(u'%s is down', (site,))

    def _request(self, url, method):
        scheme, host = urlparse(url)[:2]
        scheme = scheme.lower()
        proxies = getproxies_environment()
        if scheme in proxies:
            scheme, host = urlparse(proxies[scheme])[:2]
            scheme = scheme.lower()

        if scheme == "https":
            conn = HTTPSConnection(host)
        else:
            conn = HTTPConnection(host)

        headers={}
        if method == 'GET':
            headers['Range'] = 'bytes=0-%s' % self.max_size
        conn.request(method.upper(), url, headers=headers)

        response = conn.getresponse()

        data = response.read()
        conn.close()

        return response.status, response.reason, data

# vi: set et sta sw=4 ts=4:
