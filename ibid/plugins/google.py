from cgi import parse_qs
from httplib import BadStatusLine
import re
from urllib import quote
from urllib2 import build_opener, urlopen, HTTPCookieProcessor, Request
from urlparse import urlparse

from BeautifulSoup import BeautifulSoup

from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import decode_htmlentities, ibid_version, json_webservice, cacheable_download

help = {'google': u'Retrieves results from Google and Google Calculator.'}

default_user_agent = 'Mozilla/5.0'
default_referer = "http://ibid.omnia.za.net/"

class GoogleAPISearch(Processor):
    u"""google [for] <term>
    googlefight [for] <term> and <term>"""

    feature = 'google'

    api_key = Option('api_key', 'Your Google API Key (optional)', None)
    referer = Option('referer', 'The referer string to use (API searches)', default_referer)

    def _google_api_search(self, query, resultsize="large", country=None):
        params = {
            'v': '1.0',
            'q': query,
            'rsz': resultsize,
        }
        if country is not None:
            params['gl'] = country
        if self.api_key:
            params['key'] = self.api_key

        headers = {'referer': self.referer}
        return json_webservice('http://ajax.googleapis.com/ajax/services/search/web', params, headers)

    @match(r'^google(?:\.com?)?(?:\.([a-z]{2}))?\s+(?:for\s+)?(.+?)$')
    def search(self, event, country, query):
        try:
            items = self._google_api_search(query, country=country)
        except BadStatusLine:
            event.addresponse(u"Google appears to be broken (or more likely, my connection to it)")
            return

        results = []
        for item in items["responseData"]["results"]:
            title = item["titleNoFormatting"]
            results.append(u'"%s" %s' % (decode_htmlentities(title), item["unescapedUrl"]))

        if results:
            event.addresponse(u' :: '.join(results))
        else:
            event.addresponse(u"Wow! Google couldn't find anything")

    @match(r'^(?:rank|(?:google(?:fight|compare|cmp)))\s+(?:for\s+)?(.+?)\s+and\s+(.+?)$')
    def googlefight(self, event, term1, term2):
        try:
            count1 = int(self._google_api_search(term1, "small")["responseData"]["cursor"].get("estimatedResultCount", 0))
            count2 = int(self._google_api_search(term2, "small")["responseData"]["cursor"].get("estimatedResultCount", 0))
        except BadStatusLine:
            event.addresponse(u"Google appears to be broken (or more likely, my connection to it)")
            return

        event.addresponse(u'%(firstterm)s wins with %(firsthits)i hits, %(secondterm)s had %(secondhits)i hits',
            (count1 > count2 and {
                'firstterm':  term1,
                'firsthits':  count1,
                'secondterm': term2,
                'secondhits': count2,
            } or {
                'firstterm':  term2,
                'firsthits':  count2,
                'secondterm': term1,
                'secondhits': count1,
            }))

# Unfortunatly google API search doesn't support all of google search's
# features.
# Dear Google: We promise we don't bite.
class GoogleScrapeSearch(Processor):
    u"""gcalc <expression>
    gdefine <term>
    google.<TLD> [for] <terms>"""

    feature = 'google'

    user_agent = Option('user_agent', 'HTTP user agent to present to Google (for non-API searches)', default_user_agent)
    google_scrape_url = "http://www.google.com/search?q=%s"

    def _google_scrape_search(self, query, country=None):
        url = self.google_scrape_url
        if country:
            url += "&cr=country%s" % country.upper()
        f = urlopen(Request(url % quote(query), headers={'user-agent': self.user_agent}))
        soup = BeautifulSoup(f.read())
        f.close()
        return soup

    @match(r'^gcalc\s+(.+)$')
    def calc(self, event, expression):
        soup = self._google_scrape_search(expression)

        font = soup.find('font', size='+1')
        if not font:
            event.addresponse(u'No result')
        else:
            event.addresponse(font.b.string)

    @match(r'^gdefine\s+(.+)$')
    def define(self, event, term):
        soup = self._google_scrape_search("define:%s" % term)

        definitions = []
        for li in soup.findAll('li'):
            definitions.append(decode_htmlentities(li.contents[0].strip()))

        if definitions:
            event.addresponse(u' :: '.join(definitions))
        else:
            event.addresponse(u'Are you making up words again?')

class UnknownLanguageException (Exception): pass

help['translate'] = u'''Translates a phrase using Google Translate.'''
class Translate(Processor):
    u"""translate <phrase> [from <language code>] [to <language code>]"""

    feature = 'translate'
    
    api_key = Option('api_key', 'Your Google API Key (optional)', None)
    referer = Option('referer', 'The referer string to use (API searches)', default_referer)
    dest_lang = Option('dest_lang', 'Destination language when none is specified', 'en')

    @match(r'^translate\s+(.*?)(?:\s+from\s+(.+?))?(?:\s+to\s+(.+?))?$')
    def translate (self, event, phrase, src_lang, dest_lang):
        try:
            if dest_lang:
                dest_lang = self.language_code(dest_lang)
            else:
                dest_lang = self.dest_lang

            if src_lang:
                src_lang = self.language_code(src_lang)
            else:
                src_lang = ''
        except UnknownLanguageException:
            event.addresponse("I've never heard of that language.")
            return

        params = {'v': '1.0',
                    'q': phrase,
                    'langpair': src_lang + '|' + dest_lang}
        if self.api_key:
            params['key'] = self.api_key

        headers = {'referer': self.referer}

        response = json_webservice(
            'http://ajax.googleapis.com/ajax/services/language/translate',
            params, headers)

        if response['responseStatus'] == 200:
            translated = decode_htmlentities(
                response['responseData']['translatedText'])
            
            event.addresponse(translated)
        else:
            errors = {'invalid translation language pair':
                        "I don't know that language",
                     'invalid text':
                        "there's not much to go on",
                     'could not reliably detect source language':
                        "I'm not sure what language that was"}

            msg = errors.get(response['responseDetails'],
                            response['responseDetails'])

            event.addresponse(u"I couldn't translate that: %s.", msg)

    def language_code (self, name):
        name = name.lower()

        if re.match('^[a-z]{2}(?:-[a-z]{2})?$', name):
            return name
        if 'simplified' in name:
            return 'zh-CN'
        if 'traditional' in name:
            return 'zh-TW'
        if re.search(u'bokm[a\N{LATIN SMALL LETTER A WITH RING ABOVE}]l', name):
            # what Google calls Norwegian seems to be Bokmal
            return 'no'

        filename = cacheable_download('http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt',
                                        'google/ISO-639-2_utf-8.txt')

        pat = r'^.*(?:^|[;|])' + name + '(?:$| languages|, langues|[;|]).*$'
        m = re.search(pat, file(filename).read(), re.IGNORECASE | re.MULTILINE)

        if m is None:
            raise UnknownLanguageException
        else:
            code = m.group(0).split('|')[2]
            if code:
                return code
            else:
                raise UnknownLanguageException

# This Plugin uses code from youtube-dl
# Copyright (c) 2006-2008 Ricardo Garcia Gonzalez
# Released under MIT Licence

help['youtube'] = u'Determine the title and a download URL for a Youtube Video'
class Youtube(Processor):
    u'<Youtube URL>'

    feature = 'youtube'

    @match(r'^(?:youtube(?:\.com)?\s+)?'
        r'(?:http://)?(?:\w+\.)?youtube\.com/'
        r'(?:v/|(?:watch(?:\.php)?)?\?(?:.+&)?v=)'
        r'([0-9A-Za-z_-]+)(?(1)[&/].*)?$')
    def youtube(self, event, id):
        url = 'http://www.youtube.com/watch?v=' + id
        opener = build_opener(HTTPCookieProcessor())
        opener.addheaders = [('User-Agent', default_user_agent)]
        video_webpage = opener.open(url).read()
        title = re.search(r'<title>\s*YouTube\s+-\s+([^<]*)</title>',
                video_webpage, re.M | re.I | re.DOTALL).group(1).strip()
        t = re.search(r', "t": "([^"]+)"', video_webpage).group(1)
        event.addresponse(u'%(title)s: %(url)s', {
            'title': title,
            'url': 'http://www.youtube.com/get_video?video_id=%s&t=%s' % (id, t),
        })

# vi: set et sta sw=4 ts=4:
