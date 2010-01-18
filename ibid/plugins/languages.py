from random import choice
import re

from dictclient import Connection

from ibid.plugins import Processor, match
from ibid.config import Option, IntOption
from ibid.utils import decode_htmlentities, json_webservice, human_join

help = {}

help['dict'] = u'Defines words and checks spellings.'
class Dict(Processor):
    u"""spell <word> [using <strategy>]
    define <word> [using <dictionary>]
    (dictionaries|strategies)
    (dictionary|strategy) <name>"""
    feature = 'dict'

    server = Option('server', 'Dictionary server hostname', 'localhost')
    port = IntOption('port', 'Dictionary server port number', 2628)

    @staticmethod
    def reduce_suggestions(suggestions):
        "Remove duplicate suggestions and suffixes"
        output = []
        for s in suggestions:
            s = s.getword()
            if not s.startswith('-') and s not in output:
                output.append(s)
        return output

    @match(r'^(?:define|dict)\s+(.+?)(?:\s+using\s+(.+))?$')
    def define(self, event, word, dictionary):
        connection = Connection(self.server, self.port)
        dictionary = dictionary is None and '*' or dictionary.lower()
        dictionaries = connection.getdbdescs().keys()

        if dictionary != '*' and dictionary not in dictionaries:
            event.addresponse(
                    u"I'm afraid I don't have a dictionary of that name. I know about: %s",
                    human_join(sorted(dictionaries)))
            return

        definitions = connection.define(dictionary, word.encode('utf-8'))
        if definitions:
            event.addresponse(u', '.join(d.getdefstr() for d in definitions))
        else:
            suggestions = connection.match(dictionary, 'lev', word.encode('utf-8'))
            if suggestions:
                event.addresponse(
                        u"I don't know about %(word)s. Maybe you meant %(suggestions)s?", {
                            'word': word,
                            'suggestions': human_join(
                                self.reduce_suggestions(suggestions),
                                conjunction=u'or'),
                })
            else:
                event.addresponse(u"I don't have a definition for that. Is it even a word?")

    @match(r'^spell\s+(.+?)(?:\s+using\s+(.+))?$')
    def handle_spell(self, event, word, strategy):
        connection = Connection(self.server, self.port)
        word = word.encode('utf-8')
        strategies = connection.getstratdescs().keys()

        if connection.match('*', 'exact', word):
            event.addresponse(choice((
                u'That seems correct. Carry on',
                u'Looks good to me',
                u"Yup, that's a word all right",
                u'Yes, you *can* spell',
            )))
            return

        strategy = strategy is None and 'lev' or strategy.lower()
        if strategy not in strategies:
            event.addresponse(
                    u"I'm afraid I don't know about such a strategy. I know about: %s",
                    human_join(sorted(strategies)))

        suggestions = connection.match('*', strategy, word)
        if suggestions:
            event.addresponse(u'Suggestions: %s', human_join(
                    self.reduce_suggestions(suggestions), conjunction=u'or'))
        else:
            event.addresponse(u"That doesn't seem correct, but I can't find anything to suggest")

    @match(r'^dictionaries$')
    def handle_dictionaries(self, event):
        connection = Connection(self.server, self.port)
        dictionaries = connection.getdbdescs()
        event.addresponse(u'My Dictionaries: %s', human_join(sorted(dictionaries.keys())))

    @match(r'^strater?gies$')
    def handle_strategies(self, event):
        connection = Connection(self.server, self.port)
        strategies = connection.getstratdescs()
        event.addresponse(u'My Strategies: %s', human_join(sorted(strategies.keys())))

    @match(r'^dictionary\s+(.+?)$')
    def handle_dictionary(self, event, dictionary):
        connection = Connection(self.server, self.port)
        dictionaries = connection.getdbdescs()
        dictionary = dictionary.lower()
        if dictionary in dictionaries:
            event.addresponse(unicode(dictionaries[dictionary]))
        else:
            event.addresponse(u"I don't have that dictionary")

    @match(r'^strater?gy\s+(.+?)$')
    def handle_strategy(self, event, strategy):
        connection = Connection(self.server, self.port)
        strategies = connection.getstratdescs()
        strategy = strategy.lower()
        if strategy in strategies:
            event.addresponse(unicode(strategies[strategy]))
        else:
            event.addresponse(u"I don't have that strategy")

default_user_agent = 'Mozilla/5.0'
default_referer = "http://ibid.omnia.za.net/"

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

# vi: set et sta sw=4 ts=4:
