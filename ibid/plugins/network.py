from dns.resolver import query, NoAnswer, NXDOMAIN

from ibid.plugins import Processor, match

class DNS(Processor):

	@match(r'^(dns|nslookup|a|aaaa|ns|cname|mx|txt|spf|srv|sshfp|cert)\s+(?:for\s+)?(.+?)$')
	def resolve(self, event, record, host):
		record = record.upper()
		if record == 'DNS' or record == 'NSLOOKUP':
			record = 'A'

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
