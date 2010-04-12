% IBID-SETUP(1) Ibid Multi-protocol Bot | Ibid 0.1
% Stefano Rivera
% March 2010

# NAME

ibid-setup - Create a basic configuration file and database for an Ibid bot

# SYNOPSIS

**ibid-setup**

# DESCRIPTION

This program sets up everything that a new Ibid bot needs before it can run.
It asks a series of questions about the new bot, and writes out a basic
configuration file - `ibid.ini` (5) - to the current directory.
It also creates a database for the bot, by default a SQLite database in the
current directory.

This should be run in the directory which will become the new Ibid bot's base.

Should there be an existing **ibid.ini** in the current directory, it will be
used, and the only questions asked will be for adding an administrative user.
These can safely be skipped with a **^C**.

# FILES

*ibid.ini*
:	The Ibid bot's configuration file, will be created if it doesn't exist.

# SEE ALSO

`ibid` (1),
`ibid.ini` (5),
http://ibid.omnia.za.net/
