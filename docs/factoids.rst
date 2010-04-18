Factoids
========

.. highlight:: irc

Factoids are one of the most important Ibid plugins.
They are what give a bot most of its personality, and after a few years
on IRC, it can expect to pick up a few thousand of them from its users.

While it can store simple factoids like::

   <Alice> Ibid is an awesome bot written in Python
   <ibid> If you say so
   <Alice> Ibid
   <ibid> Ibid is an awesome bot written in Python

It can also allow for some basic behaviour programming::

   <Alice> slap $arg is <action>slaps $1 and runs for his life
   <ibid> Got it
   <Alice> slap Bob
   * ibid slaps Bob and runs for his life

Basics
------

Factoids start out pretty basic, as a way of the bot remembering things,
such as::

   <Alice> ibid: Ibid is an awesome bot framework
   <ibid> Alice: One learns a new thing every day

Now I can ask him about that::

   <Alice> ibid: what is ibid?
   <ibid> Alice: Ibid is an awesome bot framework

Or even::

   <Alice> ibid: Ibid
   <ibid> Alice: Ibid is an awesome bot framework

They can also store multiple values. On retrieval, a value is picked at
random::

   <Alice> ibid: Ibid is also your father
   <ibid> Alice: I'll remember that
   <Alice> ibid: Ibid
   <ibid> Alice: ibid is your father
   <Alice> ibid: Ibid
   <ibid> Alice: ibid is an awesome bot framework

You can request a specific one::

   <Alice> ibid: Ibid /frame/
   <ibid> Alice: ibid is an awesome bot framework
   <Alice> ibid: literal ibid
   <ibid> Alice: 1: is an awesome bot framework, 2: is your father
   <Alice> ibid: Ibid #2
   <ibid> Alice: ibid is your father

Fancy factoids
--------------

Factoids don't just have to be like a dictionary, they can have some
basic behaviour attached.
This example also shows how you can trivially replace factoids (assuming you
have permission to do so)::

   <Alice> ibid: hi is <reply>Hi there
   <ibid> Alice: One learns a new thing every day
   <Alice> ibid: hi
   <ibid> Hi there
   <Alice> ibid: no, hi is <action>waves
   <ibid> Alice: Got it
   <Alice> ibid: hi
    * ibid waves
   <Alice> ibid: no, hi is <reply>Hello $who
   <ibid> Alice: If you say so
   <Alice> ibid: hi
   <ibid> Hello Alice

The ``$who`` substitutes the speaker's name. Other substitutions possible are:

* ``$channel``, ``$source``
* ``$year``, ``$month``, ``$mon``, ``$month1``, ``$month2``, ``$day``,
  ``$day2``, ``$hour``, ``$minute``, ``$second``,
  ``$date``, ``$time``, ``$weekday``, ``$unixtime``

``$month``, ``$mon``, ``$month1`` and ``$month2`` substitute, respectively, the
month name, abbreviated month name, month number and zero-padded month number;
``$day2`` substitutes the zero-padded day number.

And factoids can have multiple names. Our greeting only responds to "hi", it
should respond to more greetings::

   <Alice> ibid: hello is the same as hi
   <ibid> Alice: Yessir
   <Alice> ibid: good day is the same as hi
   <ibid> Alice: Alrighty
   <Alice> ibid: good day
   <ibid> Hello Alice

Finally, factoids can take basic arguments::

   <Alice> ibid: slap $arg is <action>slaps $1
   <ibid> Alice: Got it
   <Alice> ibid: slap Alice
    * ibid slaps Alice
   <Alice> ibid: run from $arg to $arg is <action>starts running at $1 and stops at $2
   <ibid> Alice: One learns a new thing every day
   <Alice> ibid: run from here to there
    * ibid starts running at here and stops at there

Searching
---------

Factoids aren't very useful if we can't remember what they are called::

   <Alice> ibid: search slap
   <ibid> Alice: slap $arg [1]
   <Alice> ibid: search father
   <ibid> Alice: Ibid [2]

The first example tells us about a factoid mentioning slap.
The second shows what happens when a multi-valued factoid is found. The
result we are after may be one of two values, so we can't simply say
"``ibid: ibid``", we should rather use say::

   <Alice> ibid: ibid /father/
   <ibid> Alice: Ibid is your father

You can specify which part of the factoid you are searching in::

   <Alice> ibid: search for values containing awesome
   <ibid> Alice: Ibid [2]
   <Alice> ibid: search for names containing awesome
   <ibid> Alice: I couldn't find anything with that name

Modification
------------

Factoids aren't set in stone.
While they can be replaced with "``no, name is newvalue``", sometimes
you just want to make a small change::

   <Alice> ibid: ibid
   <ibid> Alice: Ibid is an awesome bot framework
   <Alice> ibid: ibid += , written in python
   <ibid> Alice: Pattern matches multiple factoids, please be more specific
   <Alice> ibid: ibid /awesome/ += , written in python
   <ibid> Alice: Done
   <Alice> ibid: ibid /awesome/
   <ibid> Alice: Ibid is an awesome bot framework, written in python
   <Alice> ibid: ibid /python/ ~= s/awesome //
   <ibid> Alice: Yessir
   <Alice> ibid: ibid /python/
   <ibid> Alice: Ibid is an bot framework, written in python

.. note::

   The replacement is a simple search & replace.
   If you want to use a regular expression, you must add an ``r`` flag.
   E.g. s/fo+/bar/r

   The ``i`` and ``g`` flags are also supported, as is the ``y/x/y/``
   operation.

And finally, removal::

   <Alice> ibid: forget ibid
   <ibid> Alice: Sure
   <Alice> ibid: ibid
   <ibid> Alice: What?

Or only one of the values::

   <Alice> ibid: literal ibid
   <ibid> Alice: 0: is your father, 1: is an awesome bot framework
   <Alice> ibid: forget ibid /framework/
   <ibid> Alice: Sure
   <Alice> ibid: literal ibid
   <ibid> Alice: 0: is your father

.. vi: set et sta sw=3 ts=3:
