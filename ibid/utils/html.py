# Copyright (c) 2009-2010, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import cgi
import inspect
import zlib
import urllib2
from gzip import GzipFile
from StringIO import StringIO

from html5lib import HTMLParser, treebuilders
from BeautifulSoup import BeautifulSoup

from ibid.compat import ElementTree
from ibid.utils import url_to_bytestring

class ContentTypeException(Exception):
    pass

def get_html_parse_tree(url, data=None, headers={}, treetype='beautifulsoup'):
    "Request a URL, parse with html5lib, and return a parse tree from it"

    req = urllib2.Request(url_to_bytestring(url), data, headers)
    f = urllib2.urlopen(req)

    if f.info().gettype() not in ('text/html', 'application/xhtml+xml'):
        f.close()
        raise ContentTypeException("Content type isn't HTML, but " + f.info().gettype())

    data = f.read()
    f.close()

    encoding = None
    contentType = f.headers.get('content-type')
    if contentType:
        (mediaType, params) = cgi.parse_header(contentType)
        encoding = params.get('charset')

    compression = f.headers.get('content-encoding')
    if compression:
        if compression.lower() == "deflate":
            try:
                data = zlib.decompress(data)
            except zlib.error:
                data = zlib.decompress(data, -zlib.MAX_WBITS)
        elif compression.lower() == "gzip":
            compressedstream = StringIO(data)
            gzipper = GzipFile(fileobj=compressedstream)
            data = gzipper.read()

    if treetype == "beautifulsoup":
        return BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
    elif treetype == "etree":
        kwargs = {'tree': treebuilders.getTreeBuilder('etree', ElementTree)}
        # http://code.google.com/p/html5lib/issues/detail?id=138
        if ('namespaceHTMLElements'
                in inspect.getargspec(HTMLParser.__init__)[0]):
            kwargs['namespaceHTMLElements'] = False
        parser = HTMLParser(**kwargs)
    else:
        if treetype == "html5lib-beautifulsoup":
            treetype = "beautifulsoup"
        parser = HTMLParser(tree=treebuilders.getTreeBuilder(treetype))

    return parser.parse(data, encoding = encoding)

# vi: set et sta sw=4 ts=4:
