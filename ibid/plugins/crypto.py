from crypt import crypt
import hashlib
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

# vi: set et sta sw=4 ts=4:
