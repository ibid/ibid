import re

from dns.resolver import query, NoAnswer, NXDOMAIN
from dns.reversename import from_address

from ibid.plugins import Processor, match

help = {}
ipaddr = re.compile('\d+\.\d+\.\d+\.\d+')

help['dns'] = u'Performs DNS lookups'
class DNS(Processor):
	"""(dns|nslookup|<record type>) [for] <host>"""

	feature = 'dns'

	@match(r'^(dns|nslookup|a|aaaa|ptr|ns|cname|mx|txt|spf|srv|sshfp|cert)\s+(?:for\s+)?(.+?)$')
	def resolve(self, event, record, host):
		record = record.upper()
		if record == 'DNS' or record == 'NSLOOKUP':
			record = 'A'

		if ipaddr.search(host):
			host = from_address(host)
			record = 'PTR'

		try:
			answers = query(host, str(record))
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
