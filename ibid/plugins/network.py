import re
from subprocess import Popen, PIPE

from dns.resolver import Resolver, NoAnswer, NXDOMAIN
from dns.reversename import from_address

from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output

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
            event.addresponse(u"I couldn't find any %s records for %s" % (record, host))
            return
        except NXDOMAIN:
            event.addresponse(u"I couldn't find the domain %s" % host)
            return

        responses = []
        for rdata in answers:
            responses.append(unicode(rdata))

        event.addresponse(u', '.join(responses))

help['ping'] = u'ICMP pings the specified host.'
class Ping(Processor):
    u"""ping <host>"""
    feature = 'ping'

    ping = Option('ping', 'Path to ping executable', 'ping')

    def setup(self):
        if not file_in_path(self.ping):
            raise Exception("Cannot locate ping executeable")

    @match(r'^ping\s+(\S+)$')
    def handle_ping(self, event, host):
        if host.strip().startswith("-"):
            event.addresponse(False)
            return

        ping = Popen([self.ping, '-q', '-c5', host], stdout=PIPE, stderr=PIPE)
        output, error = ping.communicate()
        code = ping.wait()

        if code == 0:
            output = unicode_output(' '.join(output.splitlines()[-2:]))
            event.addresponse(output)
        else:
            error = unicode_output(error.replace('\n', ' ').replace('ping:', '', 1).strip())
            event.addresponse(error)

help['tracepath'] = u'Traces the path to the given host.'
class Tracepath(Processor):
    u"""tracepath <host>"""
    feature = 'tracepath'

    tracepath = Option('tracepath', 'Path to tracepath executable', 'tracepath')

    def setup(self):
        if not file_in_path(self.tracepath):
            raise Exception("Cannot locate tracepath executeable")

    @match(r'^tracepath\s+(\S+)$')
    def handle_tracepath(self, event, host):

        tracepath = Popen([self.tracepath, host], stdout=PIPE, stderr=PIPE)
        output, error = tracepath.communicate()
        code = tracepath.wait()

        if code == 0:
            output = unicode_output(output)
            for line in output.splitlines():
                event.addresponse(line)
        else:
            error = unicode_output(error.strip())
            event.addresponse(error.replace('\n', ' '))

help['ipcalc'] = u'IP address calculator'
class IPCalc(Processor):
    u"""ipcalc <network> <subnet>
    ipcalc <address> - <address>"""
    feature = 'ipcalc'

    ipcalc = Option('ipcalc', 'Path to ipcalc executable', 'ipcalc')

    deaggregate_re = re.compile(r'^((?:\d{1,3}\.){3}\d{1,3})\s+-\s+((?:\d{1,3}\.){3}\d{1,3})$')

    def setup(self):
        if not file_in_path(self.ipcalc):
            raise Exception("Cannot locate ipcalc executeable")

    @match(r'^ipcalc\s+(.+)$')
    def handle_ipcalc(self, event, parameter):
        if parameter.strip().startswith("-"):
            event.addresponse(False)
            return
        
        m = self.deaggregate_re.match(parameter)
        if m:
            parameter = [m.group(1), '-', m.group(2)]
        else:
            parameter = [parameter]
        
        ipcalc = Popen([self.ipcalc, '-n', '-b'] + parameter, stdout=PIPE, stderr=PIPE)
        output, error = ipcalc.communicate()
        code = ipcalc.wait()

        if code == 0:
            output = unicode_output(output)
            if output.startswith("INVALID ADDRESS"):
                event.addresponse(u"That's an invalid address. Try something like 192.168.1.0/24")
            else:
                for line in output.splitlines():
                    if line.strip():
                        event.addresponse(line)
        else:
            error = unicode_output(error.strip())
            event.addresponse(error.replace('\n', ' '))

# vi: set et sta sw=4 ts=4:
