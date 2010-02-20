# Copyright (c) 2009-2010, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import logging
import re
import time

from ibid.config import Option, IntOption
from ibid.plugins import Processor, match
from ibid.utils import cacheable_download

features = {'rfc': {
    'description': u'Looks up RFCs by number or title.',
    'categories': ('lookup', 'web', 'development',),
}}

cachetime = 60*60
log = logging.getLogger("plugin.rfc")

class RFCLookup(Processor):
    u"""rfc <number>
    rfc [for] <search terms>
    rfc [for] /regex/"""
    feature = ('rfc',)

    indexurl = Option('index_url', "A HTTP url for the RFC Index file", "http://www.rfc-editor.org/rfc/rfc-index.txt")
    cachetime = IntOption("cachetime", "Time to cache RFC index for", cachetime)
    indexfile = None
    last_checked = 0

    def _update_list(self):
        if not self.indexfile or time.time() - self.last_checked > self.cachetime:
            self.indexfile = cacheable_download(self.indexurl, "rfc/rfc-index.txt")
            self.last_checked = time.time()

    class RFC(object):

        special_authors = (
                "Ed\.", "Eds\.", "RFC Editor", "IAP", "et al\.",
                "IAB", "IAB and IESG", "Internet Architecture Board",
                "Defense Advanced Research Projects Agency", "Internet Activities Board",
                "Gateway Algorithms and Data Structures Task Force",
                "International Organization for Standardization",
                "IAB Advisory Committee", "Federal Networking Council",
                "Internet Engineering Steering Group",
                "The Internet Society", "Sun Microsystems",
                "KOI8-U Working Group", "ISOC Board of Trustees",
                "Internet Assigned Numbers Authority \(IANA\)",
                "The North American Directory Forum",
                "Vietnamese Standardization Working Group",
                "ESnet Site Coordinating Comittee \(ESCC\)",
                "Energy Sciences Network \(ESnet\)",
                "North American Directory Forum",
                "Stanford Research Institute", "National Research Council",
                "Information Sciences Institute University of Southern California",
                "Bolt Beranek and Newman Laboratories",
                "International Telegraph and Telephone Consultative Committee of the International Telecommunication Union",
                "National Bureau of Standards", "Network Technical Advisory Group",
                "National Science Foundation", "End-to-End Services Task Force",
                "NetBIOS Working Group in the Defense Advanced Research Projects Agency",
                "ESCC X.500/X.400 Task Force",
        )
        # She's pretty, isn't she?
        # Beginners guide:
        # First line is title, initials
        # Second is middle names, surnames, and suffixes
        # Third is date and extensions
        record_re = re.compile(r"^(.+?)\. ((?:(?:[A-Z]{1,2}|[A-Z]\.-?[A-Z]|[A-Z]-[A-Z]|[A-Z]\([A-Z]\)|[A-Z][a-z]+)\.{0,2}"
            r"(?: (?:[Vv]an|[Dd]e[nr]?|[Ll][ae]|El|Del|Dos|da))* ?[a-zA-Z\-']+(?:[\.,]? (?:\d+(?:rd|nd|st|th)|Jr|I+)\.?)?|%s)"
            r"(?:, ?)?)+\. ([A-Z][a-z]{2,8}(?: \d{1,2})? \d{4})\. \((.+)\)$" % "|".join(special_authors))
        extensions_re = re.compile(r"\) \(")

        def __init__(self, number, record):
            self.number = number
            self.record = unicode(record, encoding="ASCII")

            self.issued = not self.record == "Not Issued."
            self.summary = self.record

        def parse(self):
            if self.issued:
                m = self.record_re.match(self.record)
                if not m:
                    log.warning("CAN'T DECODE RFC: " + self.record)
                else:
                    self.title, self.authors, self.date, extensions = m.groups()
                    extensions = self.extensions_re.split(extensions)
                    self.formats = []
                    self.status = None
                    self.also = None
                    self.obsoleted = self.obsoletes = None
                    self.updated = self.updates = None
                    self.online = True
                    for ex in extensions:
                        if ex.startswith("Format:"):
                            self.formats = [fmt.strip() for fmt in ex.split(":", 1)[1].split(",")]
                        elif ex.startswith("Status:"):
                            self.status = ex.split(":", 1)[1].strip()
                        elif ex == "Not online":
                            self.online = False
                        else:
                            values = [fmt.strip() for fmt in ex.split(" ", 1)[1].split(",")]
                            values = [val[:3] == "RFC" and val[3:] or val for val in values]
                            if ex.startswith("Also"):
                                self.also = values
                            elif ex.startswith("Obsoleted by"):
                                self.obsoleted = values
                            elif ex.startswith("Obsoletes"):
                                self.obsoletes = values
                            elif ex.startswith("Updated by"):
                                self.updated = values
                            elif ex.startswith("Updates"):
                                self.updates = values
                            else:
                                log.warning("CAN'T DECODE RFC: " + self.record)

                    extensions = [":" in ex and ex.split(":", 1) or ex.split(" ", 1) for ex in extensions if ":" in ex]
                    extensions = dict([(name.strip().upper(), values.strip()) for name, values in extensions])
                    self.extensions = extensions
                    self.summary = u"%s. %s." % (self.title, self.date)
                    if self.status:
                        self.summary += u" " + self.status
                    if self.obsoleted:
                        self.summary += u" Obsoleted by " + u", ".join(self.obsoleted)

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
            line = line.strip()
            if line:
                buf += " " + line
            elif buf:
                number, desc = buf.strip().split(None, 1)
                number = int(number)
                rfcs[number] = self.RFC(number, desc)
                buf = ""

        return rfcs

    @match(r'^rfc\s+#?(\d+)$')
    def lookup(self, event, number):
        rfcs = self._parse_rfcs()

        number = int(number)
        if number in rfcs:
            event.addresponse(u"%(record)s http://www.rfc-editor.org/rfc/rfc%(number)i.txt", {
                'record': rfcs[number].record,
                'number': number,
            })
        else:
            event.addresponse(u"Sorry, no such RFC")

    @match(r'^rfc\s+(?:for\s+)?(.+)$')
    def search(self, event, terms):
        # If it's an RFC number, lookup() will catch it
        if terms.isdigit():
            return

        rfcs = self._parse_rfcs()

        # Search engines:
        pool = rfcs.itervalues()
        if len(terms) > 2 and terms[0] == terms[-1] == "/":
            try:
                term_re = re.compile(terms[1:-1], re.I)
            except re.error:
                event.addresponse(u"Couldn't search. Invalid regex: %s", re.message)
                return
            pool = [rfc for rfc in pool if term_re.search(rfc.record)]

        else:
            terms = set(terms.split())
            for term in terms:
                pool = [rfc for rfc in pool if term.lower() in rfc.record.lower()]

        # Newer RFCs matter more:
        pool.reverse()

        if pool:
            results = []
            for result in pool[:5]:
                result.parse()
                results.append("%04i: %s" % (result.number, result.summary))
            event.addresponse(u'Found %(found)i matching RFCs. Listing %(listing)i: %(results)s', {
                'found': len(pool),
                'listing': min(len(pool), 5),
                'results': u',  '.join(results),
            })
        else:
            event.addresponse(u"Sorry, can't find anything")

# vi: set et sta sw=4 ts=4:
