import re

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
