Factoids
========

Factoids are one of the most important Ibid plugins.
They are what give a bot most of its personality, and after a few years
on IRC, it can expect to pick up a few thousand of them from its users.

While it can store simple factoids like::

   Me: Ibid is an awesome bot written in Python
   ibid: If you say so
   Me: Ibid
   ibid: Ibid is an awesome bot written in Python

It can also allow for some basic behaviour programming::

   Me: slap $arg is <action>slaps $1 and runs for his life
   ibid: Got it
   Me: slap Knab
   * ibid slaps Knab and runs for his life

Basics
------

Factoids start out pretty basic, as a way of the bot remembering things,
such as::

   <tumbleweed> tibid: Ibid is an awesome bot framework
   <tibid> tumbleweed: One learns a new thing every day

Now I can ask him about that::

   <tumbleweed> tibid: what is ibid?
   <tibid> tumbleweed: Ibid is an awesome bot framework

Or even::

   <tumbleweed> tibid: Ibid
   <tibid> tumbleweed: Ibid is an awesome bot framework

They can also store multiple values. On retrieval, a value is picked at
random::

   <tumbleweed> tibid: Ibid is also my father
   <tibid> tumbleweed: I'll remember that
   <tumbleweed> tibid: Ibid
   <tibid> tumbleweed: ibid is my father
   <tumbleweed> tibid: Ibid
   <tibid> tumbleweed: ibid is an awesome bot framework

You can request a specific one::

   <tumbleweed> tibid: Ibid /frame/
   <tibid> tumbleweed: ibid is an awesome bot framework
   <tumbleweed> tibid: literal ibid
   <tibid> tumbleweed: 1: is an awesome bot framework, 2: is my father
   <tumbleweed> tibid: Ibid #2
   <tibid> tumbleweed: ibid is my father

Fancy factoids
--------------

Factoids don't just have to be like a dictionary, they can have some
basic behaviour attached.
This example also shows how you can trivially replace factoids (assuming you
have permission to do so)::

   <tumbleweed> tibid: hi is <reply>Hi there
   <tibid> tumbleweed: One learns a new thing every day
   <tumbleweed> tibid: hi
   <tibid> Hi there
   <tumbleweed> tibid: no, hi is <action>waves
   <tibid> tumbleweed: Got it
   <tumbleweed> tibid: hi
    * tibid waves
   <tumbleweed> tibid: no, hi is <reply>Hello $who
   <tibid> tumbleweed: If you say so
   <tumbleweed> tibid: hi
   <tibid> Hello tumbleweed

The ``$who`` substitutes the speaker's name. Other substitutions possible are:

* ``$channel``
* ``$year``, ``$month``, ``$day``, ``$hour``, ``$minute``, ``$second``,
  ``$date``, ``$time``, ``$dow``, ``$unixtime``

And factoids can have multiple names. Our greeting only responds to "hi", it
should respond to more greetings::

   <tumbleweed> tibid: hello is the same as hi
   <tibid> tumbleweed: Yessir
   <tumbleweed> tibid: good day is the same as hi
   <tibid> tumbleweed: Alrighty
   <tumbleweed> tibid: good day
   <tibid> Hello tumbleweed

Finally, factoids can take basic arguments::

   <tumbleweed> tibid: slap $arg is <action>slaps $1
   <tibid> tumbleweed: Got it
   <tumbleweed> tibid: slap tumbleweed
    * tibid slaps tumbleweed
   <tumbleweed> tibid: run from $arg to $arg is <action>starts running at $1 and stops at $2
   <tibid> tumbleweed: One learns a new thing every day
   <tumbleweed> tibid: run from here to there
    * tibid starts running at here and stops at there

Searching
---------

Factoids aren't very useful if we can't remember what they are called::

   <tumbleweed> tibid: search slap
   <tibid> tumbleweed: slap $arg [1]
   <tumbleweed> tibid: search father
   <tibid> tumbleweed: Ibid [2]

The first example tells us about a factoid mentioning slap.
The second shows what happens when a multi-valued factoid is found. The
result we are after may be one of two values, so we can't simply say
"``tibid: ibid``", we should rather use say::

   <tumbleweed> tibid: ibid /father/
   <tibid> tumbleweed: Ibid is my father

You can specify which part of the factoid you are searching in::

   <tumbleweed> tibid: search for values containing awesome
   <tibid> tumbleweed: Ibid [2]
   <tumbleweed> tibid: search for names containing awesome
   <tibid> tumbleweed: I couldn't find anything with that name

Modification
------------

Factoids aren't set in stone.
While they can be replaced with "``no, name is newvalue``", sometimes
you just want to make a small change::

   <tumbleweed> tibid: ibid
   <tibid> tumbleweed: Ibid is an awesome bot framework
   <tumbleweed> tibid: ibid += , written in python
   <tibid> tumbleweed: Pattern matches multiple factoids, please be more specific
   <tumbleweed> tibid: ibid /awesome/ += , written in python
   <tibid> tumbleweed: Done
   <tumbleweed> tibid: ibid /awesome/
   <tibid> tumbleweed: Ibid is an awesome bot framework, written in python
   <tumbleweed> tibid: ibid /python/ ~= s/awesome //
   <tibid> tumbleweed: Yessir
   <tumbleweed> tibid: ibid /python/
   <tibid> tumbleweed: Ibid is an bot framework, written in python

.. note::

   The replacement is a simple search & replace.
   If you want to use a regular expression, you must add an ``r`` flag.
   E.g. s/fo+/bar/r

   The ``i`` and ``g`` flags are also supported, as is the ``y/x/y/``
   operation.

And finally, removal::

   <tumbleweed> tibid: forget ibid
   <tumbleweed> tibid: ibid
   <tibid> tumbleweed: What?

Or only one of the values::

   <tumbleweed> tibid: literal ibid
   <tibid> tumbleweed: 0: is my father, 1: is an awesome bot framework
   <tumbleweed> tibid: forget ibid /framework/
   <tibid> tumbleweed: Sure
   <tumbleweed> tibid: literal ibid
   <tibid> tumbleweed: 0: is my father

.. vi: set et sta sw=3 ts=3:
