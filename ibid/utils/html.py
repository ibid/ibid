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
from ibid.utils import cacheable_download, url_to_bytestring

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
        parser = HTMLParser(tree=treebuilders.getTreeBuilder(treetype))

    return parser.parse(data, encoding = encoding)

def get_country_codes():
    # The XML download doesn't include things like UK, so we consume this steaming pile of crud instead
    filename = cacheable_download('http://www.iso.org/iso/country_codes/iso_3166_code_lists/iso-3166-1_decoding_table.htm', 'lookup/iso-3166-1_decoding_table.htm')
    etree = get_html_parse_tree('file://' + filename, treetype='etree')
    table = [x for x in etree.getiterator('table')][2]

    countries = {}
    for tr in table.getiterator('tr'):
        abbr = [x.text for x in tr.getiterator('div')][0]
        eng_name = [x.text for x in tr.getchildren()][1]

        if eng_name and eng_name.strip():
            # Cleanup:
            if u',' in eng_name:
                eng_name = u' '.join(reversed(eng_name.split(',', 1)))
            eng_name = u' '.join(eng_name.split())

            countries[abbr.upper()] = eng_name.title()

    return countries

# vi: set et sta sw=4 ts=4:
