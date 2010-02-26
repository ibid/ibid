# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera, Russell Cloran,
#                          Adrian Moisey
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from crypt import crypt
import base64
import re

from ibid.compat import hashlib
from ibid.plugins import Processor, match, authorise

help = {}

help['hash'] = u'Calculates numerous cryptographic hash functions.'
class Hash(Processor):
    u"""(md5|sha1|sha224|sha256|sha384|sha512) <string>
    crypt <string> <salt>"""
    feature = 'hash'

    @match(r'^(md5|sha1|sha224|sha256|sha384|sha512)(?:sum)?\s+(.+?)$')
    def hash(self, event, hash, string):
        func = getattr(hashlib, hash.lower())
        event.addresponse(unicode(func(string.encode('utf-8')).hexdigest()))

    @match(r'^crypt\s+(.+)\s+(\S+)$')
    def handle_crypt(self, event, string, salt):
        event.addresponse(unicode(crypt(string.encode('utf-8'), salt.encode('utf-8'))))

help['base64'] = u'Encodes and decodes base 16, 32 and 64. Assumes UTF-8.'
class Base64(Processor):
    u"""base(16|32|64) (encode|decode) <string>"""
    feature = 'base64'

    @match(r'^b(?:ase)?(16|32|64)\s*(enc|dec)(?:ode)?\s+(.+?)$')
    def base64(self, event, base, operation, string):
        operation = operation.lower()
        func = getattr(base64, 'b%s%sode' % (base, operation))
        if operation == 'dec':
            try:
                bytes = func(string)
                event.addresponse(u"Assuming UTF-8: '%s'", unicode(bytes, 'utf-8', 'strict'))
            except TypeError, e:
                event.addresponse(u"Invalid base%(base)s: %(error)s",
                        {'base': base, 'error': unicode(e)})
            except UnicodeDecodeError:
                event.addresponse(u'Not UTF-8: %s', unicode(repr(bytes)))
        else:
            event.addresponse(unicode(func(string.encode('utf-8'))))

help['rot13'] = u'Transforms a string with ROT13.'
class Rot13(Processor):
    u"""rot13 <string>"""
    feature = 'rot13'

    @match(r'^rot13\s+(.+)$')
    def rot13(self, event, string):
        repl = lambda x: x.group(0).encode('rot13')
        event.addresponse(re.sub('[a-zA-Z]+', repl, string))

help['dvorak'] = u"Makes text typed on a QWERTY keyboard as if it was Dvorak work, and vice-versa"
class Dvorak(Processor):
    u"""(aoeu|asdf) <text>"""
    feature = 'dvorak'

    # List of characters on each keyboard layout
    dvormap = u"""',.pyfgcrl/=aoeuidhtns-;qjkxbmwvz"<>PYFGCRL?+AOEUIDHTNS_:QJKXBMWVZ[]{}|"""
    qwermap = u"""qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?-=_+|"""

    # Typed by a QWERTY typist on a Dvorak-mapped keyboard
    typed_on_dvorak = dict(zip(map(ord, dvormap), qwermap))
    # Typed by a Dvorak typist on a QWERTY-mapped keyboard
    typed_on_qwerty = dict(zip(map(ord, qwermap), dvormap))

    @match(r'^(?:asdf|dvorak)\s+(.+)$')
    def convert_from_qwerty(self, event, text):
        event.addresponse(text.translate(self.typed_on_qwerty))

    @match(r'^(?:aoeu|qwerty)\s+(.+)$')
    def convert_from_dvorak(self, event, text):
        event.addresponse(text.translate(self.typed_on_dvorak))

help['retest'] = u'Checks whether a regular expression matches a given string.'
class ReTest(Processor):
    u"""does <pattern> match <string>"""
    feature = 'retest'
    permission = 'regex'

    @match('^does\s+(.+?)\s+match\s+(.+?)$')
    @authorise(fallthrough=False)
    def retest(self, event, regex, string):
        event.addresponse(re.search(regex, string) and u'Yes' or u'No')

help["morse"] = u"Translates messages into and out of morse code."
class Morse(Processor):
    u"""morse (text|morsecode)"""
    feature = 'morse'

    _table = {
        'A': ".-",
        'B': "-...",
        'C': "-.-.",
        'D': "-..",
        'E': ".",
        'F': "..-.",
        'G': "--.",
        'H': "....",
        'I': "..",
        'J': ".---",
        'K': "-.-",
        'L': ".-..",
        'M': "--",
        'N': "-.",
        'O': "---",
        'P': ".--.",
        'Q': "--.-",
        'R': ".-.",
        'S': "...",
        'T': "-",
        'U': "..-",
        'V': "...-",
        'W': ".--",
        'X': "-..-",
        'Y': "-.--",
        'Z': "--..",
        '0': "-----",
        '1': ".----",
        '2': "..---",
        '3': "...--",
        '4': "....-",
        '5': ".....",
        '6': "-....",
        '7': "--...",
        '8': "---..",
        '9': "----.",
        ' ': " ",
        '.': ".-.-.-",
        ',': "--..--",
        '?': "..--..",
        ':': "---...",
        ';': "-.-.-.",
        '-': "-....-",
        '_': "..--.-",
        '"': ".-..-.",
        "'": ".----.",
        '/': "-..-.",
        '(': "-.--.",
        ')': "-.--.-",
        '=': "-...-",
    }
    _rtable = dict((v, k) for k, v in _table.items())

    def _text2morse(self, text):
        return u" ".join(self._table.get(c.upper(), c) for c in text)

    def _morse2text(self, morse):
        toks = morse.split(u' ')
        return u"".join(self._rtable.get(t, u' ') for t in toks)

    @match(r'^morse\s*(.*)$', 'deaddressed')
    def morse(self, event, message):
        if not (set(message) - set(u'-./ \t\n')):
            event.addresponse(u'Decodes as %s', self._morse2text(message))
        else:
            event.addresponse(u'Encodes as %s', self._text2morse(message))

# vi: set et sta sw=4 ts=4:
