from gzip import GzipFile
from htmlentitydefs import name2codepoint
import os
import os.path
import re
from StringIO import StringIO
from threading import Lock
import time
from urllib import urlencode
import urllib2
import zlib

from dateutil.tz import tzlocal, tzutc

import ibid
from ibid.compat import defaultdict, json

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

downloads_in_progress = defaultdict(Lock)
def cacheable_download(url, cachefile, headers={}):
    """Download url to cachefile if it's modified since cachefile.
    Specify cachefile in the form pluginname/cachefile.
    Returns complete path to downloaded file."""

    downloads_in_progress[cachefile].acquire()
    try:
        f = _cacheable_download(url, cachefile, headers)
    finally:
        downloads_in_progress[cachefile].release()

    return f

def _cacheable_download(url, cachefile, headers={}):
    # We do allow absolute paths, for people who know what they are doing,
    # but the common use case should be pluginname/cachefile.
    if cachefile[0] not in (os.sep, os.altsep):
        cachedir = ibid.config.plugins['cachedir']
        if not cachedir:
            cachedir = os.path.join(ibid.options['base'], 'cache')
        elif cachedir[0] == "~":
            cachedir = os.path.expanduser(cachedir)
        cachedir = os.path.abspath(cachedir)

        plugindir = os.path.join(cachedir, os.path.dirname(cachefile))
        if not os.path.isdir(plugindir):
            os.makedirs(plugindir)

        cachefile = os.path.join(cachedir, cachefile)

    exists = os.path.isfile(cachefile)

    req = urllib2.Request(url)
    for name, value in headers:
        req.add_header(name, value)
    if not req.has_header('user-agent'):
        req.add_header('User-Agent', 'Ibid/' + (ibid_version() or 'dev'))

    if exists:
        if os.path.isfile(cachefile + '.etag'):
            f = file(cachefile + '.etag', 'r')
            req.add_header("If-None-Match", f.readline().strip())
            f.close()
        else:
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

    etag = connection.headers.get('etag')
    if etag:
        f = file(cachefile + '.etag', 'w')
        f.write(etag + '\n')
        f.close()

    outfile = file(cachefile, 'wb')
    outfile.write(data)
    outfile.close()

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
    try:
        from pkg_resources import get_distribution, DistributionNotFound
        try:
            package = get_distribution('Ibid')
            if package and hasattr(package, 'version'):
                return package.version
        except DistributionNotFound:
            pass
    except ImportError:
        pass

def format_date(timestamp, length='datetime', tolocaltime=True):
    "Format a UTC date for displaying in a response"

    defaults = {
            u'datetime_format': u'%Y-%m-%d %H:%M:%S %Z',
            u'date_format': u'%Y-%m-%d',
            u'time_format': u'%H:%M:%S %Z',
    }

    length += '_format'
    format = ibid.config.plugins.get(length, defaults[length])

    if tolocaltime:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=tzutc())
        timestamp = timestamp.astimezone(tzlocal())

    return unicode(timestamp.strftime(format.encode('utf8')), 'utf8')

class JSONException(Exception):
    pass

def json_webservice(url, params={}, headers={}):
    "Request data from a JSON webservice, and deserialise"

    for key in params:
        if isinstance(params[key], unicode):
            params[key] = params[key].encode('utf-8')

    if params:
        url += '?' + urlencode(params)

    req = urllib2.Request(url, headers=headers)
    if not req.has_header('user-agent'):
        req.add_header('User-Agent', 'Ibid/' + (ibid_version() or 'dev'))

    f = urllib2.urlopen(req)
    data = f.read()
    f.close()
    try:
        return json.loads(data)
    except ValueError, e:
        raise JSONException(e)

def human_join(items, separator=u',', conjunction=u'and'):
    "Create a list like: a, b, c and d"
    items = list(items)
    separator += u' '
    return ((u' %s ' % conjunction)
            .join(filter(None, [separator.join(items[:-1])] + items[-1:])))

def plural(count, singular, plural):
    "Return sigular or plural depending on count"
    if count == 1:
        return singular
    return plural

# vi: set et sta sw=4 ts=4:
