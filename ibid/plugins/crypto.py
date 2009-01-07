from crypt import crypt
from hashlib import md5, sha1, sha224, sha256, sha384, sha512
import re

import ibid
from ibid.plugins import Processor, match, handler

help = {}

hashes =    {   'md5': md5,
                'sha1': sha1,
                'sha224': sha224,
                'sha256': sha256,
                'sha384': sha384,
                'sha512': sha512
            }

help['hash'] = 'Calculates numerous cryptographic hash functions.'
class Hash(Processor):
    """(md5|sha1|sha224|sha256|sha384|sha512|crypt) <string> [<salt>]"""
    feature = 'hash'

    def setup(self):
        self.hash.im_func.pattern = re.compile(r'^(%s)\s+(.+?)$' % '|'.join(hashes.keys()), re.I)

    @handler
    def hash(self, event, hash, string):
        hash = hash.lower()
        event.addresponse(hashes[hash](string).hexdigest())

    @match(r'^crypt\s+(.+)\s+(\S+)$')
    def handle_crypt(self, event, string, salt):
        event.addresponse(crypt(string, salt))

# vi: set et sta sw=4 ts=4:
