% IBID-DB(1) Ibid Multi-protocol Bot | Ibid 0.1
% Stefano Rivera
% March 2010

# NAME

ibid-db - Database management utility for Ibid

# SYNOPSIS

**ibid-db** *command* [*options*...]

# DESCRIPTION

This utility is for offline management of your Ibid bot's database.  Used for
import, export, and upgrades.

The export format is DBMS-agnostic and can be used to migrate between different
databases.

# COMMANDS

**-e** *FILE*, **--export**=*FILE*
:	Export DB contents to *FILE*.
	Export format is JSON.
	*FILE* can be **-** for *stdout* or can end in **.gz** for automatic gzip
	compression.

**-i** *FILE*, **--import**=*FILE*
:	Import DB contents from *FILE* as exported by this utility.
	*FILE* can be **-** for *stdin* or can end in **.gz** for automatic gzip
	compression.

:	**Note:** The DB must be empty first.

**-u**, **--upgrade**
:	Upgrade DB schema to the latest version.
	You need to run this after upgrading your bot.

:	**Note:** You should backup first.

# OPTIONS

**--version**
:	Show the program's version and exit.

**-h**, **--help**
:	Show a help message and exit.

**-v**, **--verbose**
:	Turn on debugging output to stderr.

# FILES

*ibid.ini*
:	Locates the database to act upon by looking for the
	[**databases**].**ibid** value in the bot configuration file in the current
	directory.

# SEE ALSO
`ibid` (1),
`ibid.ini` (5),
`ibid-setup` (1),
http://ibid.omnia.za.net/
