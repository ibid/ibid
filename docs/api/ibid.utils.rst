:mod:`ibid.utils` -- Helper functions for plugins
=================================================

.. module:: ibid.utils
   :synopsis: Helper functions for plugins
.. moduleauthor:: Ibid Core Developers

This module contains common functions that many Ibid plugins can use.

String Functions
----------------

.. function:: ago(delta, units=None)

   Return a string representation of *delta*, a
   :class:`datetime.timedelta`.

   If *units*, an integer, is specified then only that many units of
   time will be used.

   .. code-block:: pycon

      >>> ago(datetime.utcnow() - datetime(1970, 1, 1))
      '39 years, 6 months, 12 days, 9 hours, 59 minutes and 14 seconds'
      >>> ago(datetime.utcnow() - datetime(1970, 1, 1), 2)
      '39 years and 6 months'

.. function:: format_date(timestamp, length='datetime')

   Convert :class:`datetime.datetime` *timestamp* to the local timezone
   (*timestamp* is assumed to be UTC if it has no *tzinfo*) and return a
   unicode string representation.

   *length* can be one of ``'datetime'``, ``'date'`` and ``'time'``,
   specifying what to include in the output.

   The format is specified in the ``plugins.length`` configuration
   subtree, as three values: ``datetime_format``, ``date_format`` and
   ``time_format``.

   Example::

      >>> format_date(datetime.utcnow())
      u'2009-12-14 12:41:55 SAST'

.. function:: human_join(items, separator=u',', conjunction=u'and')

   Turn iterable *items* into a unicode list in the format ``a, b, c
   and d``.

   *separator* separates all values except the last two, separated by
   *conjunction*.

   Example::

      >>> human_join(['a', 'b', 'c', 'd'])
      u'a, b, c and d'

.. function:: plural(count, singular, plural)

   If *count* is 1, return *singular*, otherwise *plural*.

.. function:: decode_htmlentities(text)

   Return *text* with all HTML entities removed, both numeric and
   string-style.

.. function:: file_in_path(program)

   Returns a boolean indicating whether the program of name *program*
   can be found, using the ``PATH`` environment variable.

   Similar to ``which`` on the command line.

.. function:: unicode_output(output, errors='strict')

   Decodes *output* a string, to unicode, using the character set
   specified in the ``LANG`` environment variable.
   *errors* has the same behaviour as the builtin :func:`unicode`.

   Useful for parsing program output.

.. function:: ibid_version()

   Return the current Ibid version or ``None`` if no version can be
   determined.

Web Service Functions
---------------------

.. function:: cacheable_download(url, cachefile, headers={})

   Useful for data files that you don't want to keep re-downloading, but
   do occasionally change.

   *url* is a URL to download, to a file named *cachefile*.
   *cachefile* should be in the form of ``pluginname/filename``.
   It will be stored in the configured ``plugins.cachedir`` and the full
   filename returned.
   Extra HTTP headers in *headers* can be supplied, if necessary.

   If *cachefile* already exists, :func:`cacheable_download` will do an
   *If-Modified-Since* HTTP request.
   It handles HTTP-compression.

   Example::

      filename = cacheable_download(
         'http://www.iso.org/iso/country_codes/iso_3166_code_lists/iso-3166-1_decoding_table.htm',
         'lookup/iso-3166-1_decoding_table.htm')

.. function:: json_webservice(url, params={}, headers={})

   Request *url*, with optional parameters *params* and headers
   *headers*, and parse as JSON.

   :exc:`JSONException` will be raised if the returned data isn't valid
   JSON.

.. exception:: JSONException(Exception)

   Raised by :func:`json_webservice` if invalid JSON is returned.

:mod:`ibid.utils.html` -- HTML Parsing
--------------------------------------

.. module:: ibid.utils.html
   :synopsis: HTML Parsing helper functions for plugins
.. moduleauthor:: Ibid Core Developers

.. function:: get_html_parse_tree(url, data=None, headers={}, treetype='beautifulsoup)

   Request *url*, and return a parse-tree of type *treetype*.
   *data* and *headers* are optionally used in the request.

   *treetype* can be any type supported by :mod:`html5lib`, most
   commonly ``'etree'`` or ``'beautifulsoup'``.

   :exc:`ContentTypeException` will be raised if the returned data isn't
   HTML.

.. exception:: ContentTypeException(Exception)

   Raised by :func:`get_html_parse_tree` if the content type isn't HTML.

.. vi: set et sta sw=3 ts=3:
