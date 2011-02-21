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

Lines can be commented out by prefixing them with ``#``.

Top Level Options
^^^^^^^^^^^^^^^^^

.. describe:: botname:

   String: The name of the bot.
   It will respond to this name.

.. describe:: logging:

   String: The location of the :mod:`logging` configuration file.

   Default: ``logging.ini``

.. describe:: mysql_engine:

   String: The engine that MySQL tables will be created in.

   Default: ``InnoDB``

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

   List: Authentication methods that can be used on all sources.

.. describe:: timeout:

   Number: Time in seconds that authentication should be cached for
   before requiring re-authentication.

.. describe:: permissions:

   List: Permissions that are granted to everyone.
   Although they can be overridden for specific users, using the online
   grant function.

   The name of the permission can be prefixed with a ``+`` to indicate
   that this permission is granted without requiring authentication.
   Or a ``-`` to revoke a permission granted to all users of a source.

   See :ref:`the list of permissions <permissions>`.

Sources
^^^^^^^

Sources are the way that Ibid connects to users.
Every IRC/SILC/DC server is it's own source as are connections to other
services.

The configuration parameters that applies to all sources are:

.. describe:: disabled:

   Boolean: Every source can be disabled from auto-starting by setting
   this to ``True`` in the source`s configuration.

.. describe:: type:

   String: The driver that this source should use.
   This allows you to have more than one IRC source, for example.

   Default: The name of the source.
   If you specify a type, you are free to name the source anything you
   want to.

.. describe:: permissions:

   List: This lets you grant and revoke permissions to all users on the
   source.
   They can be overridden for specific users, using the online grant
   function.

   The name of the permission can be prefixed with a ``+`` to indicate
   that this permission is granted without requiring authentication.
   Or a ``-`` to revoke a permission granted to all users of a source.

   See :ref:`the list of permissions <permissions>`.

IRC Source
""""""""""

Some of the IRC functionality (i.e. NickServ authentication and
joining/parting channels) is handled by the ``irc`` plugin.

.. describe:: server:

   **Reqired**
   String: The hostname of the IRC server to connect to.

   Ibid :bug:`does not currently support <363466>` falling back to
   alternate servers, so you may want to use a round-robin hostname.

.. describe:: port:

   Number: The port to connect to.

   Default: ``6667``

.. describe:: ssl:

   Boolean: Use SSL-encrypted connection to the network.

   Default: ``False``

.. describe:: nick:

   String: The nickname for the bot to use on this network.

   Default: The :obj:`botname`

.. describe:: modes:

   String: The IRC modes to set.
   Some servers require bots to set mode ``B``.

   Default: nothing

.. describe:: channels:

   List: Channels to join on connection to the network.

   .. warning::
      You must include the leading ``#``, but unless you quote each
      channel, Ibid will see the rest of the config line as a comment.

      So use quotes around each channel name like this: ``"#ibid",
      "#fun"``

.. describe:: nickserv_password:

   String: The password identifying your bot to NickServ.
   If set, the bot will respond to authentication requests from
   NickServ.

   Default: Nothing

.. describe:: nickserv_mask:

   String: The NickServ's hostmask on this network.
   You can set this to ensure that you don't accidentally give your
   NickServ password to an imposter, should the network's services
   module go down.

   You can use glob wildcards, i.e. ``*`` and ``?``.

   Default: ``*``

.. describe:: nickserv_nick:

   String: The NickServ's nickname on this network.
   You probably won't need to change it.

   Default: ``NickServ``

.. describe:: ping_interval:

   Number: How many seconds in between each keep-alive PING sent to the
   server.

   Default: ``60``

.. describe:: pong_timeout:

   Number: How long to wait for PONGs before giving up and reconnecting.

   Default: ``300``

Jabber Source
"""""""""""""

.. describe:: jid:

   **Required**
   String: The jabber ID that the bot will connect with.
   (This looks like an e-mail address)

.. describe:: password:

   **Required**
   String: The password for the supplied JID.

.. describe:: rooms:

   List: MUC chatrooms to join on connection.

   Default: Nothing

.. describe:: accept_domains:

   List: Domains that the bot will accept messages from.
   If this isn't set, it'll accept messages from anyone.

   Default: Nothing (i.e. no restriction)

.. describe:: server:

   String: The hostname of the server to connect to.

   Default: Determined automatically from the jabber ID.

.. describe:: port:

   Number: The port to connect to.

   Default: ``5222`` or ``5223`` if :obj:`ssl` is ``True``

.. describe:: ssl:

   Boolean: Use old port 5223-style SSL connection instead of
   opportunistic TLS on port 5222.

   Default: ``False``

.. describe:: nick:

   String: The nickname for the bot to use on this server when in MUC
   chatrooms.

   Default: The :obj:`botname`

.. describe:: max_public_message_length:

   Number: The bot will limit public (i.e. MUC) messages to this length
   (in bytes) to avoid flooding the channel with long messages.

   Default: ``512``

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
