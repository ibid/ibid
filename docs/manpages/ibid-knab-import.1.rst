==================
 ibid-knab-import
==================

SYNOPSIS
========

``ibid-knab-import`` *knab-sa-url* *source* [*config-file*]

DESCRIPTION
===========

This utility imports users, last seen information, factoids, and URLs
from a Knab bot's database into an Ibid.

For best results, import directly into a brand new, clean Ibid install.

On import, strings are converted to Unicode, guessing UTF-8 and falling
back to detection.

OPTIONS
=======

knab-sa-url
   The SQLAlchemy URI for the Knab's database.
   The format is
   ``mysql://``\ *user*\ ``:``\ *pass*\ ``@``\ *hostname*\ ``/``\ *dbname*

source
   The name in the Ibid bot for the source that the Knab was previously
   connected to.

config-file
   If supplied, this is configuration file is used for locating the
   Ibid's database rather than ``ibid.ini``.

FILES
=====

ibid.ini
   Locates the database to act upon by looking for the
   [**databases**].\ **ibid** value in the bot configuration file in the
   current directory.

SEE ALSO
========

``ibid``\ (1),
``ibid.ini``\ (5),
``ibid-setup``\ (1),
http://ibid.omnia.za.net/,
http://knab.omnia.za.net/

.. vi: set et sta sw=3 ts=3:
