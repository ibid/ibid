Ibid Plugin Tutorial
====================

This will guide you through the process of creating an Ibid plugin so
you can add your own features.

Getting Started
---------------

Install an Ibid
^^^^^^^^^^^^^^^

.. highlight:: text

Before we can write a plugin, we need a working base Ibid install.
There are :ref:`better instructions <installation>` for a more permanent
installation, but here's how you get a quick install for some
development.

Install the Python packages you'll need::

   user@box $ sudo aptitude install bzr python-configobj python-sqlalchemy \
        python-twisted python-beautifulsoup python-celementtree \
        python-html5lib python-pysqlite2 python-simplejson \
        python-soappy python-jinja python-dateutil

Install an Ibid from the current development trunk.
We'll use the default shortcut developer configuration, which uses a
SQLite database called ``ibid.db`` in your current directory::

   user@box ~ $ bzr branch lp:ibid
   user@box ~ $ cd ibid
   user@box ~/ibid $ scripts/ibid-setup
   ... Messages about setting up tables
   Database tables created
   Please enter the details for your account. This account will be given
   full admin permissions.
   Nick/JID: ^D

You can abort it at that point with a :kbd:`Control-D`, because we'll
only be debugging locally.
It'll be set up with a basic configuration for joining the current Ibid
developer IRC channel (#ibid on irc.atrum.org), as well as a SILC
network and Jabber, but we don't need that yet.
We'll be doing everything locally, without running the full-blown bot.

The Testing Environment
^^^^^^^^^^^^^^^^^^^^^^^

Rather than working on a live bot and having to reload modules a lot,
when developing for Ibid, we usually use ``ibid-plugin``, a minimal,
fast, testing environment.

It looks like this::

   user@box ~/ibid $ scripts/ibid-plugin
   ... Messages about loading plugins
   Query: hello
   Response: Huh?
   Query: help
   Response: Use "features" to get a list of available features. "help <feature>" will give a description of the feature, and "usage <feature>" will describe how to use it.
   Query: features
   Response: Features: config, core, die, help and plugins

To exit, press :kbd:`Control-C` or :kbd:`Control-D`.

As you can see, there is almost nothing loaded.
It can't even respond to "hello", the code for that is in the
*factoid* module.
If you want to load the *factoid* module, you can either say "load
factoid" or you can tell ``ibid-plugin`` to load it on startup, by
adding it as a parameter::

   user@box ~/ibid $ scripts/ibid-plugin factoid
   ... Messages about loading plugins
   Query: hi
   Response: good morning

Try talking to it too fast, it'll start ignoring you.
This makes sense for a real chat channel, but not debugging.
You can tell the *ignorer* not to load by adding it as a parameter
followed by ``-``::

   user@box ~/ibid $ scripts/ibid-plugin factoid core.Ignore-

If you want all the normal modules loaded, you can add the ``-c``
option, but it'll take quite a bit longer to start up::

   user@box ~/ibid $ scripts/ibid-plugin -c
   ... Screenfulls of messages
   Query: hello
   Response: sup

Play with that a bit.
It isn't exactly the same as a full bot, there are a few things that
won't work, but it's good enough for testing.
Some examples:

* Karma, because it's disabled for private conversations by default.
  You can switch to public mode with ``-p``.
* The games, because they require some advanced Twisted functionality
  (as well as other channel members).

Ibid Theory
-----------

Ibid is divided into two main parts (excluding the Ibid core code):
*Sources* and *Plugins*.

The sources speak IRC, Jabber, e-Mail, etc.
There is one source for each network that the bot is connected to.
When someone says something in an IRC channel, the IRC source for that
network will create an *Event*.
The event is passed to the plugins, which each take a turn to look at it
and decide if they want to do anything.
If a plugin decides to reply, the event is sent back to the source to
dispatch the reply.

Events are also used for, private messages from users to the bot, people
joining and leaving channels, etc. but most plugins don't need to deal
with anything except message events, directed to the bot.

Ibid comes with some plugins for pre- and post-processing of events
(such as logging), and some for features.

Plugin Writing Time
-------------------

Processors and Handlers
^^^^^^^^^^^^^^^^^^^^^^^

.. highlight:: python

Let's see what that looks like in practice.
Here's a simple hello world plugin.
Create a file called ``tutorial.py`` in the ``ibid/plugins`` directory,
with the following contents::

   from ibid.plugins import Processor, handler

   class HelloWorld(Processor):
      @handler
      def hello(self, event):
         event.addresponse(u'Hello World!')

A plugin can contain multiple *Processor*\ s.
Each one is a self-contained part of the event handling chain.
It can register an interest in certain types of event, or a specific
place in the chain, but for most plugins the defaults are sufficient.

Inside the processor, any functions decorated with :func:`@handler
<ibid.plugins.handler>` will get a chance to look at the event.
If it choses to add a response to the event, the response will be
returned to the user.

.. note::

   Ibid uses unicode strings and to catch mistakes, you'll get a warning
   if you pass a normal string as a response, so try to get in the habit
   of using unicode.

Test it out, anything you say to the bot should provoke a "Hello World!"
response:

.. code-block:: text

   user@box ~/ibid $ scripts/ibid-plugin tutorial
   ... Messages about loading plugins
   Query: hello
   Response: Hello World!

Now, you could include code inside your handler to determine if you want
to reply to a message or not, but must of the time you are after
messages that look like something particular, so we have another
decorator, :func:`@match() <ibid.plugins.match>`, to help you::

   from ibid.plugins import Processor, match

   class HelloWorld(Processor):
       @match(r'^hello$')
       def hello(self, event):
           event.addresponse(u'Hello World!')

Match takes a regular expression as a parameter, and will only run your
handler function if the regex matches the event's message.
In this case, it'll only fire if you say "hello".
It'll ignore trailing punctuation and whitespace, as that's removed by
the :class:`core.Strip <ibid.plugins.core.Strip>` plugin.

Match Groups
^^^^^^^^^^^^

Time for a more complex example, a multiple dice roller, you can add it
as another Processor in your tutorial plugin::

   from random import randint

   from ibid.plugins import Processor, match
   from ibid.utils import human_join

   class Dice(Processor):
       @match(r'^roll\s+(\d+)\s+dic?e$')
       def multithrow(self, event, number):
           number = int(number)
           throws = [unicode(randint(1, 6)) for i in range(number)]
           event.addresponse(u'I threw %s', human_join(throws))

If you still have an ``ibid-plugin`` open you can "reload tutorial" to
reload your plugin.

Any match groups you put in the regex will be passed to the handler as
arguments, in this case the number of dice to throw.
If you want brackets without creating a match group, you can use the
non-grouping syntax ``(?: )``.

:mod:`ibid.utils` contains many handy helper functions.
:func:`human_join() <ibid.utils.human_join>` is the equivalent of ``u',
'.join()``, with an "and" before the last item.

:meth:`addresponse() <ibid.event.Event.addresponse>` takes a second
argument for string substitution.  If you want to substitute multiple
items, use the dict syntax::

   event.addresponse(u'Nobody %(verb)s the %(noun)s!', {
       'verb': u'expects',
       'noun': u'Spanish Inquisition',
   })

Documentation
^^^^^^^^^^^^^

At the moment you'll see that your plugin doesn't appear in *features*,
you can fix that with a little more code::

   from random import randint

   from ibid.plugins import Processor, match
   from ibid.utils import human_join

   help = {}

   help['dice'] = u'Throws multiple dice'

   class Dice(Processor):
       u'roll <number> dice'

       feature = 'dice'

       @match(r'^roll\s+(\d+)\s+dic?e$')
       def multithrow(self, event, number):
           number = int(number)
           throws = [unicode(randint(1, 6)) for i in range(number)]
           event.addresponse(u'I threw %s', human_join(throws))

The module-level ``help`` dict specifies descriptions for features
(*help* command) and the doc-string of the processor gives the
*usage*.
"reload tutorial" and you should see "dice" appear in *features*.

Configuration
-------------

Ibid has a configuration system that may be useful for your plugin.
Configuration values can be set at runtime or by editing ``ibid.ini``.

Let's make the number of dice sides be configurable::

   from random import randint

   from ibid.config import IntOption
   from ibid.plugins import Processor, match
   from ibid.utils import human_join

   class Dice(Processor):
       sides = IntOption('sides', 'Number of sides to each die', 6)

       @match(r'^roll\s+(\d+)\s+dic?e$')
       def multithrow(self, event, number):
           number = int(number)
           throws = [unicode(randint(1, self.sides)) for i in range(number)]
           event.addresponse(u'I threw %s', human_join(throws))

:class:`IntOption() <ibid.config.IntOption>` creates a configuration
value called ``plugins.tutorial.sides`` with a default value of 6.
There are also configuration helpers for other data types.

If you merge the following into your ``ibid.ini``, you can change to 21
sided dice:

.. code-block:: ini

   [plugins]
      [[tutorial]]
         sides = 21

Style
-----

Now that you've got all the basics, here are some other things you
should know about writing Ibid plugins.

Error Handling
^^^^^^^^^^^^^^

You might have noticed that we haven't said anything about error
handling.
That was intentional.
All exceptions in plugins are caught at the dispatcher level, and an
appropriate response will be returned to the user, as well as tracebacks
logged.
The only time you should worry about handling errors is if you can
recover gracefully or you want to return a specific response (such as an
explanation).

Responses
^^^^^^^^^

The general Ibid style is that the bot should be something people can
relate to, not too mechanical.
So many Ibid responses are playful and maybe a little snarky.
Also, many responses aren't static, but rather chosen from a list of 3
or 4 at random (:func:`random.choice` is good for that).

Next Steps
----------

That's it, you are now more than able to write your own Ibid plugins.
Please :ref:`send us <contributing>` anything you write, it may be
useful for other people too.

We wished there was more documentation we could point you at, to help
you, but it hasn't been written yet.
So, read some modules to see what's there, and stick your nose in our
IRC channel for help.

.. vi: set et sta sw=3 ts=3:
