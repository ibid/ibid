from crypt import crypt
import hashlib
import base64
import re

import ibid
from ibid.plugins import Processor, match, handler

help = {}

help['hash'] = 'Calculates numerous cryptographic hash functions.'
class Hash(Processor):
    """(md5|sha1|sha224|sha256|sha384|sha512|crypt) <string> [<salt>]"""
    feature = 'hash'

    @match(r'(md5|sha1|sha224|sha256|sha384|sha512)\s+(.+?)$')
    def hash(self, event, hash, string):
        hash = hash.lower()
        event.addresponse(eval('hashlib.%s' % hash)(string).hexdigest())

    @match(r'^crypt\s+(.+)\s+(\S+)$')
    def handle_crypt(self, event, string, salt):
        event.addresponse(crypt(string, salt))

help['base64'] = 'Encodes and decodes base 16, 32 and 64.'
class Base64(Processor):
    """b(16|32|64)(encode|decode) <string>"""
    feature = 'base64'

    @match(r'b(16|32|64)(enc|dec)(?:ode)?\s+(.+?)$')
    def base64(self, event, base, operation, string):
        event.addresponse(eval('base64.b%s%sode' % (base, operation))(string))

# vi: set et sta sw=4 ts=4:
