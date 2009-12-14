:mod:`ibid.compat` -- Python Version Compatibility
==================================================

.. module:: ibid.compat
   :synopsis: Python-version-independent imports of common modules
.. moduleauthor:: Ibid Core Developers

This module provides compatibility for older Python versions back to
2.4, allowing the use of some newer features.

The following modules and functions are available, and should be
imported from :mod:`ibid.compat` rather than elsewhere.

Modules
-------

.. describe:: email_utils

   Standard Python :mod:`email.utils`.

   Functions for parsing and formatting e-Mail headers.

.. describe:: hashlib

   Standard Python :mod:`hashlib`.

   Cryptographic hash functions.

   On Python 2.4 it won't support the SHA-2 functions:
   :func:`hashlib.sha224`, :func:`hashlib.sha384` and
   :func:`hashlib.sha512` -- these will all return ``'Not Supported'``.

.. describe:: json

   Standard Python :mod:`json`, using SimpleJSON on older versions.

   JSON serialisation and parsing library.

.. describe:: ElementTree

   Standard Python :mod:`xml.etree.cElementTree`, using ElementTree on
   older versions.

Classes
-------

.. class:: defaultdict([default_factory[, ...]])

   Standard Python :class:`collections.defaultdict`.

   Returns a dict-like-object where all unset values contain the value
   returned by *default_factory()*.

Functions
---------

.. function:: all(iterable)

   Standard Python :func:`all`.

   Return ``True`` if every item in *iterable* is ``True``.

.. function:: any(iterable)

   Standard Python :func:`any`.

   Return ``True`` if any single item in *iterable* is ``True``.

.. function:: strptime(date_string, format)

   Standard Python :func:`datetime.datetime.strptime`.

   Return a :class:`datetime <datetime.dattime>` corrosponding to
   *date_string*, according to *format*.

.. function:: factorial(x)

   Standard Python :func:`math.factorial`.

   Return the factorial of *x*.

.. vi: set et sta sw=3 ts=3:
