from urllib2 import urlopen

from BeautifulSoup import BeautifulSoup

import ibid
from ibid.plugins import Processor, match

class Bash(Processor):

	@match(r'^bash(?:\.org)?\s+(random|\d+)$')
	def bash(self, event, quote):
		f = urlopen('http://bash.org/?%s' % quote.lower())
		soup = BeautifulSoup(f.read(), convertEntities=BeautifulSoup.HTML_ENTITIES)
		f.close()

		quote = soup.find('p', attrs={'class': 'qt'})
		if not quote:
			event.addresponse(u"There's no such quote, but if you keep talking like that maybe there will be.")
		else:
			for line in quote.contents:
				if str(line) != '<br />':
					event.addresponse(str(line).strip())
