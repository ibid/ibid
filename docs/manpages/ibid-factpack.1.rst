===============
 ibid-factpack
===============

SYNOPSIS
========

| ``ibid-factpack`` [``-s``] *factpack-file*
| ``ibid-factpack`` ``-r`` [``-f``] *factpack-name*
| ``ibid-factpack`` ``-h``

DESCRIPTION
===========

This utility is for adding and removing sets of packaged factoids, known
as factpacks, from your Ibid's factoid database.

The default mode is factpack loading.
The *factpack-file* specified is loaded into the bot's database.
Should the pack contain any facts with the same name as an existing fact
in the bot's database, loading will be aborted, unless the ``-s`` option
is supplied.

Factpacks can be gzipped if the filename ends with ``.gz``.

When invoked with the ``-r`` option, the named factpack (original import
filename minus the extension) will be removed from the bot.
If any of the facts contained in that pack were modified while loaded in
the bot, unloading will be aborted, unless the ``-f`` option is
supplied.

OPTIONS
=======

-r, --remove
   Remove the named factpack, rather than importing.

-f, --force
   Force removal, if facts in the factpack were modified by users.

-s, --skip
   Skip facts that clash with existing factoids, during import.

-h, --help
   Show a help message and exit.

FACTPACKS
=========

Factpacks are JSON-encoded text files containing a list of facts.
Each fact is a tuple of two lists: fact-names, fact-values.
The same substitutions are available as in normal online Factoids.

Example:
--------
::

   [
    [["Hello", "Hi"], ["<reply> Hi There", "<action> waves"]],
    [["Bye"], ["<reply> kbye $who", "<reply> Cheers"]]
   ]

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
http://ibid.omnia.za.net/

.. vi: set et sta sw=3 ts=3:
