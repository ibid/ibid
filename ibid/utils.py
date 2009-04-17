import cgi
from gzip import GzipFile
from htmlentitydefs import name2codepoint
import os
import os.path
from pkg_resources import resource_exists, resource_string
import re
from StringIO import StringIO
import time
import urllib2
import zlib

from html5lib import HTMLParser, treebuilders

from html5lib import HTMLParser, treebuilders
from xml.etree import cElementTree
from BeautifulSoup import BeautifulSoup

import ibid

def ago(delta, units=None):
    parts = []

    for unit, value in (
            ('year', delta.days/365), ('month', delta.days/30 % 12),
            ('day', delta.days % 30), ('hour', delta.seconds/3600),
            ('minute', delta.seconds/60 % 60), ('second', delta.seconds % 60),
            ('millisecond', delta.microseconds/1000)):
        if value > 0 and (unit != 'millisecond' or len(parts) == 0):
            parts.append('%s %s%s' % (value, unit, value != 1 and 's' or ''))
            if units and len(parts) >= units:
                break

    formatted =  ' and '.join(parts)
    return formatted.replace(' and ', ', ', len(parts)-2)

def decode_htmlentities(text):
    replace = lambda match: unichr(int(match.group(1)))
    text = re.sub("&#(\d+);", replace, text)

    replace = lambda match: match.group(1) in name2codepoint and unichr(name2codepoint[match.group(1)]) or match.group(0)
    text = re.sub("&(\w+);", replace, text)
    return text

def cacheable_download(url, cachefile):
    """Download url to cachefile if it's modified since cachefile.
    Specify cachefile in the form pluginname/cachefile.
    Returns complete path to downloaded file."""

    # We do allow absolute paths, for people who know what they are doing,
    # but the common use case should be pluginname/cachefile.
    if cachefile[0] not in (os.sep, os.altsep):
        cachedir = ibid.config.plugins['cachedir']
        if not cachedir:
            cachedir = os.path.join(ibid.options['base'], 'cache')
        elif cachedir[0] == "~":
            cachedir = os.path.expanduser(cachedir)

        plugindir = os.path.join(cachedir, os.path.dirname(cachefile))
        if not os.path.isdir(plugindir):
            os.makedirs(plugindir)
    
        cachefile = os.path.join(cachedir, cachefile)

    exists = os.path.isfile(cachefile)

    req = urllib2.Request(url)

    if exists:
        modified = os.path.getmtime(cachefile)
        modified = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(modified))
        req.add_header("If-Modified-Since", modified)

    try:
        connection = urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        if e.code == 304 and exists:
            return cachefile
        else:
            raise
    
    # Download into a temporary file, in case something goes wrong
    downloadfile = os.path.join(plugindir, ".download." + os.path.basename(cachefile))
    outfile = file(downloadfile, "wb")
    data = connection.read()

    compression = connection.headers.get('content-encoding')
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

    outfile.write(data)
    
    outfile.close()

    try:
        os.rename(downloadfile, cachefile)
    except OSError:
        # Are we on a system that doesn't support atomic renames?
        os.remove(cachefile)
        os.rename(downloadfile, cachefile)
    
    return cachefile

def file_in_path(program):
    path = os.environ.get("PATH", os.defpath).split(os.pathsep)
    path = [os.path.join(dir, program) for dir in path]
    path = [True for file in path if os.path.isfile(file)]
    return bool(path)

def unicode_output(output, errors="strict"):
    try:
        encoding = os.getenv("LANG").split(".")[1]
    except:
        encoding = "ascii"
    return unicode(output, encoding, errors)

def ibid_version():
    return resource_exists(__name__, '.version') and resource_string(__name__, '.version').strip() or None

def get_html_parse_tree(url, data=None, headers={}, treetype='beautifulsoup'):
    "Request a URL, parse with html5lib, and return a parse tree from it"

    req = urllib2.Request(url, data, headers)
    f = urllib2.urlopen(req)
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
        treebuilder = treebuilders.getTreeBuilder("etree", cElementTree)
    else:
        treebuilder = treebuilders.getTreeBuilder(treetype)

    parser = HTMLParser(tree=treebuilder)

    return parser.parse(data, encoding = encoding)

# vi: set et sta sw=4 ts=4:
