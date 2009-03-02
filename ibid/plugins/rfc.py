import os.path
import time

from ibid.config import Option
from ibid.plugins import Processor, match
from ibid.utils import cacheable_download

help = {"rfc": "Looks up RFCs by number or title."}

cachetime = 60*60

class RFC(Processor):
    """rfc <number>
    rfc for <search terms>"""
    feature = "rfc"

    indexurl = Option('index_url', "A HTTP url for the RFC Index file", "http://www.rfc-editor.org/rfc/rfc-index.txt")
    indexfile = None
    last_checked = 0

    def _update_list(self):
        if not self.indexfile or time.time() - self.last_checked > cachetime:
            self.indexfile = cacheable_download(self.indexurl, "rfc/rfc-index.txt")
            self.last_checked = time.time()

    def _parse_rfcs(self):
        self._update_list()

        f = file(self.indexfile, "rU")
        lines = f.readlines()
        f.close()

        breaks = 0
        strip = -1
        for lineno, line in enumerate(lines):
            if line.startswith(20 * "~"):
                breaks += 1
            elif breaks == 2 and line.startswith("000"):
                strip = lineno
                break
        lines = lines[strip:]
    
        rfcs = {}
        buf = ""
        # So there's nothing left in buf:
        lines.append("")
        for line in lines:
            if line.strip():
                buf += " " + line.strip()
            elif buf.strip():
                number, desc = buf.strip().split(None, 1)
                rfcs[int(number)] = desc
                buf = ""

        return rfcs

    @match(r'^rfc\s+(\d+)$')
    def lookup(self, event, number):
        rfcs = self._parse_rfcs()

        number = int(number)
        if number in rfcs:
            event.addresponse(unicode(rfcs[number]))
        else:
            event.addresponse(u"Sorry, no such RFC.")

    @match(r'^rfc\s+for\s+(.+)$')
    def search(self, event, terms):
        rfcs = self._parse_rfcs()
        
        # TODO: Not much of a search engine...
        terms = set(terms.split())
        pool = rfcs.iteritems()
        for term in terms:
            pool = [(rfc, text) for rfc, text in pool if term.lower() in text.lower()]

        # Newer RFCs matter more:
        pool.reverse()

        if pool:
            event.addresponse(u"Found %i matching RFCs. Listing %i:" % (len(pool), min(len(pool), 5)))
            for result in pool[:5]:
                event.addresponse("%04i: %s" % result)
        else:
            event.addresponse("Sorry, can't find anything.")

# vi: set et sta sw=4 ts=4:
