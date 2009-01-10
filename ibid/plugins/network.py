import re
from subprocess import Popen, PIPE

from dns.resolver import Resolver, NoAnswer, NXDOMAIN
from dns.reversename import from_address

from ibid.plugins import Processor, match

help = {}
ipaddr = re.compile('\d+\.\d+\.\d+\.\d+')

help['dns'] = u'Performs DNS lookups'
class DNS(Processor):
    """(dns|nslookup|dig) [<record type>] [for] <host> [(from|@) <nameserver>]"""

    feature = 'dns'

    @match(r'^(?:dns|nslookup|dig)(?:\s+(a|aaaa|ptr|ns|soa|cname|mx|txt|spf|srv|sshfp|cert))?\s+(?:for\s+)?(\S+?)(?:\s+(?:from\s+|@)\s*(\S+))?$')
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
            responses.append(str(rdata))

        event.addresponse(', '.join(responses))

help['ping'] = 'ICMP pings the specified host.'
class Ping(Processor):
    """ping <host>"""
    feature = 'ping'

    ping = 'ping'

    @match(r'^ping\s+(\S+)$')
    def handle_ping(self, event, host):
        
        ping = Popen([self.ping, '-q', '-c5', host], stdout=PIPE, stderr=PIPE)
        output, error = ping.communicate()
        code = ping.wait()

        if code == 0:
            event.addresponse(' '.join(output.splitlines()[-2:]))
        else:
            event.addresponse(error.replace('\n', ' ').replace('ping:', '', 1).strip())

help['tracepath'] = 'Traces the path to the given host.'
class Tracepath(Processor):
    """tracepath <host>"""
    feature = 'tracepath'

    tracepath = 'tracepath'

    @match(r'^tracepath\s+(\S+)$')
    def handle_tracepath(self, event, host):

        tracepath = Popen([self.tracepath, host], stdout=PIPE, stderr=PIPE)
        output, error = tracepath.communicate()
        code = tracepath.wait()

        if code == 0:
            for line in output.splitlines():
                event.addresponse(line)
        else:
            event.addresponse(error.replace('\n', ' ').strip())

# vi: set et sta sw=4 ts=4:
