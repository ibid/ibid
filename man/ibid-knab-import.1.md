% IBID-KNAB-IMPORT(1) Ibid Multi-protocol Bot | Ibid 0.1
% Stefano Rivera
% March 2010

# NAME

ibid-knab-import - Knab->Ibid Import utility

# SYNOPSIS

**ibid-knab-import** *knab-sa-url* *source* [*config-file*]

# DESCRIPTION

This utility imports users, last seen information, factoids, and URLs from a
Knab bot's database into an Ibid.

For best results, import directly into a brand new, clean Ibid install.

On import, strings are converted to Unicode, guessing UTF-8 and falling back to
detection.

# OPTIONS

*knab-sa-url*
:	The SQLAlchemy URI for the Knab's database.
	The format is **mysql://**_user_**:**_pass_**@**_hostname_**/**_dbname_

*source*
:	The name in the Ibid bot for the source that the Knab was previously
	connected to.

*config-file*
:	If siupplied, this is configuration file is used for locating the Ibid's
	database rather than **ibid.ini**.

# FILES

*ibid.ini*
:	Locates the database to act upon by looking for the
	[**databases**].**ibid** value in the bot configuration file in the current
	directory.

# SEE ALSO

`ibid` (1),
`ibid.ini` (5),
`ibid-setup` (1),
http://ibid.omnia.za.net/,
http://knab.omnia.za.net/
