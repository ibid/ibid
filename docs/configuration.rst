.. _configuration:

Configuration
=============

.. _botdir:

The botdir
----------

Every Ibid lives in a directory, the botdir.
This holds the configuration file, logs, caches, the SQLite database if
you are using it, and plugins you've written.

The botdir should be your current directory whenever you run an
ibid-related script, so it can find the configuration file.

All non-absolute paths in the ibid configuration are relative to the
botdir.

.. note::
   The botdir is added to the front of :attr:`sys.path`, so any python
   package that you put in the botdir will be available to the bot, and
   take precedence over other versions of the same package.

The configuration file
----------------------

Ibid's configuration is stored in ``ibid.ini``, created when you
install Ibid.
You can edit it at any time and tell the bot to ``reread config`` or
edit it online with the *config* feature.

A simple example ibid.ini::

   botname = joebot
   logging = logging.ini

   [auth]
       methods = password,
       timeout = 300
       permissions = +factoid, +karma, +sendmemo, +recvmemo, +feeds, +publicresponse

   [sources]
       [[telnet]]
       [[timer]]
       [[http]]
           url = http://joebot.example.com
       [[smtp]]
       [[pb]]
       [[atrum]]
           channels = "#ibid",
           nick = $botname
           type = irc
           auth = hostmask, nickserv
           server = irc.atrum.org

   [plugins]
       cachedir = /tmp/ibid
       [[core]]
           names = $botname, bot, ant
           ignore = ,

   [databases]
       ibid = sqlite:///ibid.db

This shows the main sections of the file.
It is in configobj format, an ini-variant with nested sections.
Whitespace is ignored, all values belong to the most recently defined
section.

Top Level Options
^^^^^^^^^^^^^^^^^

.. describe:: botname:

   The name of the bot.
   It will respond to this name.

.. describe:: logging:

   Defaults to ``logging.ini``.
   The location of the :mod:`logging` configuration file.

.. describe:: mysql_engine:

   Defaults to ``InnoDB``.
   The engine that MySQL tables will be created in.

Auth
^^^^

.. vi: set et sta sw=3 ts=3:
