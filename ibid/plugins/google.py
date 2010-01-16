from httplib import BadStatusLine
import re
from urllib import quote
from urllib2 import build_opener, urlopen, HTTPCookieProcessor, Request

from BeautifulSoup import BeautifulSoup

from ibid.plugins import Processor, match
from ibid.config import Option, IntOption
from ibid.utils import decode_htmlentities, json_webservice
from ibid.utils import human_join

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
class TranslationException (Exception): pass

help['translate'] = u'''Translates a phrase using Google Translate.'''
class Translate(Processor):
    u"""translate <phrase> [from <language>] [to <language>]
        translation chain <phrase> [from <language>] [to <language>]"""

    feature = 'translate'

    api_key = Option('api_key', 'Your Google API Key (optional)', None)
    referer = Option('referer', 'The referer string to use (API searches)', default_referer)
    dest_lang = Option('dest_lang', 'Destination language when none is specified', 'english')

    chain_length = IntOption('chain_length', 'Maximum length of translation chains', 10)

    lang_names = {'afrikaans':'af', 'albanian':'sq', 'arabic':'ar',
                  'belarusian':'be', 'bulgarian':'bg', 'catalan':'ca',
                  'chinese':'zh', 'chinese simplified':'zh-cn',
                  'chinese traditional':'zh-tw', 'croatian':'hr', 'czech':'cs',
                  'danish':'da', 'dutch':'nl', 'english':'en', 'estonian':'et',
                  'filipino':'tl', 'finnish':'fi', 'french':'fr',
                  'galacian':'gl', 'german':'de', 'greek':'el', 'hebrew':'iw',
                  'hindi':'hi', 'hungarian':'hu', 'icelandic':'is',
                  'indonesian':'id', 'irish':'ga', 'italian':'it',
                  'japanese':'ja', 'korean': 'ko', 'latvian':'lv',
                  'lithuanian':'lt', 'macedonian':'mk', 'malay':'ms',
                  'maltese':'mt', 'norwegian':'no', 'persian':'fa',
                  'polish':'pl', 'portuguese':'pt', 'romanian':'ro',
                  'russian': 'ru', 'serbian':'sr', 'slovak':'sk',
                  'slovenian':'sl', 'spanish':'es', 'swahili':'sw',
                  'swedish':'sv', 'thai':'th', 'turkish':'tr', 'ukrainian':'uk',
                  'uzbek': 'uz', 'vietnamese':'vi', 'welsh':'cy',
                  'yiddish':'yi'}

    alt_lang_names = {'simplified':'zh-CN', 'simplified chinese':'zh-CN',
                   'traditional':'zh-TW', 'traditional chinese':'zh-TW',
                   'bokmal':'no', 'norwegian bokmal':'no',
                   u'bokm\N{LATIN SMALL LETTER A WITH RING ABOVE}l':'no',
                   u'norwegian bokm\N{LATIN SMALL LETTER A WITH RING ABOVE}l':
                        'no',
                   'farsi':'fa'}

    LANG_REGEX = '|'.join(lang_names.keys() + lang_names.values() +
                            alt_lang_names.keys())

    @match(r'^(?:translation\s*)?languages$')
    def languages (self, event):
        event.addresponse(human_join(sorted(self.lang_names.keys())))

    @match(r'^translate\s+(.*?)(?:\s+from\s+(' + LANG_REGEX + r'))?'
            r'(?:\s+(?:in)?to\s+(' + LANG_REGEX + r'))?$')
    def translate (self, event, text, src_lang, dest_lang):
        dest_lang = self.language_code(dest_lang or self.dest_lang)
        src_lang = self.language_code(src_lang or '')

        try:
            translated = self._translate(event, text, src_lang, dest_lang)[0]
            event.addresponse(translated)
        except TranslationException, e:
            event.addresponse(u"I couldn't translate that: %s.", unicode(e))

    @match(r'^translation[-\s]*(?:chain|party)\s+(.*?)'
            r'(?:\s+from\s+(' + LANG_REGEX + r'))?'
            r'(?:\s+(?:in)?to\s+(' + LANG_REGEX + r'))?$')
    def translation_chain (self, event, phrase, src_lang, dest_lang):
        if self.chain_length < 1:
            event.addresponse(u"I'm not allowed to play translation games.")
        try:
            dest_lang = self.language_code(dest_lang or self.dest_lang)
            src_lang = self.language_code(src_lang or '')

            chain = [phrase]
            for i in range(self.chain_length):
                phrase, src_lang = self._translate(event, phrase,
                                                    src_lang, dest_lang)
                src_lang, dest_lang = dest_lang, src_lang
                chain.append(phrase)
                if phrase in chain[:-1]:
                    break

            event.addresponse(u'\n'.join(chain[1:]), conflate=False)

        except TranslationException, e:
            event.addresponse(u"I couldn't translate that: %s.", unicode(e))

    def _translate (self, event, phrase, src_lang, dest_lang):
        params = {
            'v': '1.0',
            'q': phrase,
            'langpair': src_lang + '|' + dest_lang,
        }
        if self.api_key:
            params['key'] = self.api_key

        headers = {'referer': self.referer}

        response = json_webservice(
            'http://ajax.googleapis.com/ajax/services/language/translate',
            params, headers)

        if response['responseStatus'] == 200:
            translated = unicode(decode_htmlentities(
                response['responseData']['translatedText']))
            return (translated, src_lang or
                    response['responseData']['detectedSourceLanguage'])
        else:
            errors = {
                'invalid translation language pair':
                    u"I don't know that language",
                'invalid text':
                    u"there's not much to go on",
                 'could not reliably detect source language':
                    u"I'm not sure what language that was",
            }

            msg = errors.get(response['responseDetails'],
                            response['responseDetails'])

            raise TranslationException(msg)

    def language_code (self, name):
        """Convert a name to a language code."""

        name = name.lower()

        if name == '':
            return name

        try:
            return self.lang_names.get(name) or self.alt_lang_names[name]
        except KeyError:
            m = re.match('^([a-z]{2,3})(?:-[a-z]{2})?$', name)
            if m and m.group(1) in self.lang_names.values():
                return name
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
