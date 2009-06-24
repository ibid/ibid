from crypt import crypt
import base64
import hashlib
import re

from ibid.plugins import Processor, match

help = {}

help['hash'] = u'Calculates numerous cryptographic hash functions.'
class Hash(Processor):
    u"""(md5|sha1|sha224|sha256|sha384|sha512) <string>
    crypt <string> <salt>"""
    feature = 'hash'

    @match(r'^(md5|sha1|sha224|sha256|sha384|sha512)(?:sum)?\s+(.+?)$')
    def hash(self, event, hash, string):
        func = getattr(hashlib, hash.lower())
        event.addresponse(unicode(func(string).hexdigest()))

    @match(r'^crypt\s+(.+)\s+(\S+)$')
    def handle_crypt(self, event, string, salt):
        event.addresponse(unicode(crypt(string, salt)))

help['base64'] = u'Encodes and decodes base 16, 32 and 64.'
class Base64(Processor):
    u"""b(16|32|64)(encode|decode) <string>"""
    feature = 'base64'

    @match(r'^b(16|32|64)(enc|dec)(?:ode)?\s+(.+?)$')
    def base64(self, event, base, operation, string):
        func = getattr(base64, 'b%s%sode' % (base, operation.lower()))
        event.addresponse(unicode(func(string)))

help['rot13'] = u'Transforms a string with ROT13.'
class Rot13(Processor):
    u"""rot13 <string>"""
    feature = 'rot13'

    @match(r'^rot13\s+(.+)$')
    def rot13(self, event, string):
        repl = lambda x: x.group(0).encode('rot13')
        event.addresponse(re.sub('[a-zA-Z]+', repl, string))

# vi: set et sta sw=4 ts=4:
