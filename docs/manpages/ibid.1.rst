% IBID(1) Ibid Multi-protocol Bot | Ibid 0.1
% Stefano Rivera
% March 2010

# NAME

ibid - Run an Ibid bot

# SYNOPSIS

**ibid** [*config-file*]

# DESCRIPTION

This runs an Ibid bot in the foreground.

There should there be an existing **ibid.ini** (created by
`ibid-setup` (1))
in the current directory or one should be provided on the command line.

Where possible, you should run **twistd -n ibid** instead of this
program, as otherwise some classes of errors go unreported.
See **BUGS**.

# BUGS

Exceptions in twisted callbacks can go unnoticed in this program.
That has no harmful effects, but the developers may miss out on some
good bug reports.

# FILES

*ibid.ini*
:	The Ibid bot's configuration file, will be created if it doesn't exist.

# SEE ALSO

`ibid.ini` (5),
`ibid-setup` (1),
`twistd` (1),
http://ibid.omnia.za.net/
