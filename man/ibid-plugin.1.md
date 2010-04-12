% IBID-PLUGIN(1) Ibid Multi-protocol Bot | Ibid 0.1
% Stefano Rivera
% March 2010

# NAME

ibid-plugin \- Plugin testing developer environment for Ibid

# SYNOPSIS

**ibid-plugin** [*options*...] [*plugin*[**-**]|_plugin_**.**_Processor_[**-**]...]

# DESCRIPTION

This utility is for testing Ibid plugins without the full bot environment.
This means testing can be performed offline and without loading all the
available plugins.

This should be run in a configured Ibid bot directory.

All the listed plugins and Processors will be loaded on start-up.
Naming a plugin loads the complete plugin.
Suffixing a **-** to the name, ignores that plugin or Processor instead of
loading it.

# OPTIONS

**-c**, **-\-configured**
:	Load all configured plugins, instead of only the core and requested
	plugins.

**-o**, **-\-only**
:	Don't load the Ibid core plugins, only the plugins requested.
	Note that without the **core** plugin to pre- and post-process events, most
	other plugins won't function correctly.

**-p**, **-\-public**
:	By default, **ibid-plugin** emulates a private conversation with the bot.
	With this option, the conversation is considered to be public and the
	bot will have to be addressed to provoke a response.

**-v**, **-\-verbose**
:	Increase verbosity.
	The final form of each *Event* object will be displayed before any
	responses.

**-h**, **-\-help**
Show a help message and exit.

# FILES

*ibid.ini*
:	Locates the database to act upon by looking for the
	[**databases**].**ibid** value in the bot configuration file in the current
	directory.

# BUGS

**ibid-plugin** doesn't emulate a complete Ibid environment, and will ignore
all of the following:

* Delayed and periodically executed functions.
* Messages to alternate sources.
* Messages directly dispatched, rather than added to responses.
* Permissions. All permissions are granted to the user.

# SEE ALSO
`ibid` (1),
`ibid.ini` (5),
`ibid-setup` (1),
http://ibid.omnia.za.net/
