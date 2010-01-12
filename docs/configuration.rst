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

This section is for configuring Ibid's user-authentication.
Permissions that are granted ``…when authed`` require users to
authenticate themselves to the bot before the permission can be invoked.
Some sources have special ways of authenticating users (e.g. the
``nickserv`` authentication method on IRC) or guarantee that their users
are always authenticated via the ``imlicit`` authentication method (e.g.
jabber).

.. describe:: methods:

   List of authentication methods that can be used on all sources.

.. describe:: timeout:

   Time in seconds that authentication should be cached for before
   requiring re-authentication.

.. describe:: permissions:

   List of permissions that are granted to everyone.
   The name of the permission can be prefixed with a ``+`` to indicate
   that this permission is granted without requiring authentication.
   Or a ``-`` to revoke a permission granted to all users of a source.

   See :ref:`the list of permissions <permissions>`.

.. _permissions:

Permissions
-----------

The following permissions are used in Ibid core:

``accounts``
   Alter user's accounts.
``admin``
   Grant and revoke permissions. Shut down the bot.
``config``
   Alter configuration values online. (Rewrites the configuration file)
``core``
   Reload Ibid core components.
``plugins``
   Load and unload plugins.
``sources``
   Start and stop sources. Join and leave channels.

Other permissions used in plugins:

``chairmeeting``
   Start meeting minute-taking.
``eval``
   Execute arbitrary Python code.
``factoid``
   Set factoids and modify factoids that you have set yourself.
``factoidadmin``
   Delete / modify factoids that you didn't set in the first place.
``feeds``
   Configure RSS/Atom feeds
``karma``
   Promote or demote karma for things.
``karmaadmin``
   Delete karma items.
``recvmemo``
   Receive memos.
``saydo``
   Use the bot as a puppet.
``sendmemo``
   Send memos.
``summon``
   Summon a user via another source.

.. vi: set et sta sw=3 ts=3:
