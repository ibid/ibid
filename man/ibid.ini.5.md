% IBID.INI(5) Ibid Multi-protocol Bot | Ibid 0.1
% Stefano Rivera
% March 2010

# NAME

ibid.ini - Configuration file for Ibid

# DESCRIPTION

ibid.ini contains all the configuration for an Ibid bot.

A complete description of the contents of this file is out of the scope of this
manpage.
For more details see the Ibid documentation: http://ibid.omnia.za.net/docs/

Lines beginning with **#** are considered to be comments and ignored.
To use a **#** symbol in an option (e.g. an IRC channel name), quote the
option with double-quotes, e.g. **channels**=**"#ibid",**

This file will be written to by the bot when configuration settings are
altered online.
It can also be edited manually and a running bot told to
**"reload config"**.
Manual edits and comments will be preserved when the bot modifies its
own configuration, provided that they have not been edited since bot
start-up or the last config reload.

# SECTIONS

## auth

Settings related to permissions and authentication.
Permissions listed in **auth**.**permissions** are granted to all users unless
revoked by source or account.

## sources

Sources are Ibid connections to an IM service.
They range from IRC networks to the bot's built-in HTTP server.

Each source is configured in a section named after the source.
The source name will define the driver that the source should use, unless a
**type** option is provided.

Sources can be disabled by setting
**disabled**=**True**.

## plugins

Plugin configuration.
Each plugin is configured within a section named after the plugin.

**cachedir**
:	The directory that temporary files (such as downloaded data), useful to be
	the bot but expendable, is stored in.

**core**.**autoload**
:	If **True**, all plugins not explicitly ignored will be loaded.
	(Note that some plugins mark themselves as non-auto-loadable).
	Defaults to **True**.

**core**.**load**
:	The list of plugins (or **plugin**.**Processor**s) to load.

**core**.**noload**
:	The list of plugins (or **plugin**.**Processor**s) to ignore and not load.

**core**.**names**
:	The names that the bot should respond to.

**core**.**ignore**
:	Nicks that the bot should completely ignore (e.g. other bots).

# EXAMPLE

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

# FILES

*logging*.*ini*
:	A standard Python **logging**.**config** configuration file describing
	loggers, handlers, and formatters for log messages.
	See http://docs.python.org/library/logging.html

# SEE ALSO
`ibid` (1),
`ibid.ini` (5),
`twistd` (1),
http://ibid.omnia.za.net/
