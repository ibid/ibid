:mod:`ibid.plugins` -- Plugin registration
==========================================

.. module:: ibid.plugins
   :synopsis: Processor base class and helpers
.. moduleauthor:: Ibid Core Developers

Plugins are added to Ibid by placing a module inside :mod:`ibid.plugins`.

To do anything, the plugin must contain classes extending
:class:`Processor`.

.. class:: Processor

   Base class for Ibid plugins.
   Processors receive :class:`Events <ibid.event.Event>` and
   (optionally) do things with them.
   Plugins extend Processor to implement features.
   Each Processor occupies a single slot in the event processing queue, and
   can request specific types of events through the class attributes.

   The Processor doesn't need to be instantiated, Ibid discovers all
   Processors defined in a plugin at load time.

   .. attribute:: usage

      String: each line should be a BNF description of a function in the
      Processor.
      Leading and trailing whitespace in each line is ignored, as are
      empty lines.

      Default: ``None``

   .. attribute:: features

      List: Strings naming each feature that this Processor is part of.
      Used in locating "usage" strings for on-line documentation.

      The "description" string located inside a module-level `features`
      dict maps feature names to help strings.

      Default: empty

   .. attribute:: permission

      String: The name of the permission that :func:`authorise` methods
      in this Processor require.

      Default: ``None``

   .. attribute:: permissions

      List of Strings: The names of permissions that :func:`authorise`
      methods in this Processor check directly (using
      :func:`auth_responses`).

      Default: empty

   .. attribute:: event_types

      A tuple of :class:`Event <ibid.event.Event>` type strings that the
      Processor wishes to receive.

      Default is only messages: ``('message',)``

   .. attribute:: addressed

      Boolean flag: Whether to only receive events where the bot is
      addressed (i.e.  private chat or addressed in a channel).

      Default: ``True``

   .. attribute:: processed

      Boolean flag: Whether to receive events that are already marked as
      having been processed.

      Default: ``False``

   .. attribute:: priority

      Integer: The weight of a Processor.
      Negative numbers put a Processor earlier in the queue, positive
      later.

      Values in the range of -1000 to 1900 are sane, but outside of
      those, events will not behave normally, as pre-processing
      occurs between -2000 and -1000 and logging happens at 1900.

      Default: 0 unless :attr:`processed` is ``True``, then 1500

   .. attribute:: autoload

      Boolean flag: Whether to load the plugin or not.

      Default: ``True``

   .. method:: setup(self)

      Runs once on startup and on every configuration reload.
      Use it for setting up your Processor.

      If you implement it, call :func:`super`.

   .. method:: shutdown(self)

      Runs once on shutdown.
      Use it for cleaning up.

   .. method:: process(self, event)

      This is the core of a Processor, where events get dispatched.

      *event* is the :class:`ibid.event.Event` to process.

      .. note::

         Don't override this, instead register handlers via
         :func:`@handler <handler>` or :func:`@match() <match>`.

Decorators
----------

.. function:: handler

   Decorator that makes a method receive all events.

   First parameter to the wrapped method will be the event object::

      @handler
      def handle(self, event):
         event.addresponse(u'Did you see that? I handled an event')

.. function:: match(regex, version='clean', simple=True)

   Decorator that makes a method receive message events matching
   regular expression string *regex*.

   The *regex* will be matched, with ``re.I``, ``re.UNICODE`` and ``re.DOTALL`` modes.
   You should anchor both sides of it. If *simple* is true (default), the regex
   will be modified to match the whole string (``^`` and ``$`` are added), a space in
   the regex will match any sequence of whitespace, and the following
   shortcuts are available for common regex fragments (which are captured as
   arguments):

   ============ ==========================================
   Selector     expands to
   ============ ==========================================
   ``{alpha}``  ``[a-zA-Z]+``
   ``{any}``    ``.*``
   ``{chunk}``  ``\S+``
   ``{digits}`` ``\d+``
   ``{number}`` ``\d*\.?\d+``
   ``{url}``    :func:`url_regex() <ibid.utils.url_regex>`
   ``{word}``   ``\w+``
   ============ ==========================================

   Using simple regexes where they are applicable can make them much more
   readable.

   Any match groups or selectors in the regex will be passed as parameters to the
   decorated method, after the event object::

      @match(r'(?:foo|bar) {chunk}')
      def foo(self, event, parameter):
         event.addresponse(u'Foo: %s', parameter)

   The above match is equivalent to this non-simple version::

      @match(r'^(?:foo|bar)\s+(\S+)$', simple=False)

   *version* can be set to one of:

   ``'clean'``
      The default, and almost always what you want.
      The bot name and intervening punctuation are removed from the
      front of the message, if the bot was addressed.
      Trailing punctuation and surrounding whitespace is stripped.

   ``'raw'``
      The message as the bot saw it.

   ``'deaddressed'``
      The bot name and intervening punctuation are removed from the
      front of the message, if the bot was addressed.

   ``'stripped'``
      Trailing punctuation and surrounding whitespace is stripped.

   .. tabularcolumns:: |r|l|l|

   +-------------+-------------------+------------------+
   |             | De-address        | Don't de-address |
   +=============+===================+==================+
   | Strip       | ``'clean'``       | ``'stripped'``   |
   +-------------+-------------------+------------------+
   | Don't strip | ``'deaddressed'`` | ``'raw'``        |
   +-------------+-------------------+------------------+

.. function:: authorise(fallthrough=True)

   Decorator that requires :attr:`Processor.permission` for the user
   that would trigger this method.

   *fallthrough* sets the failure mode.
   If ``True``, the next Procesor will be called in the hope of finding
   another one that'll handle it.
   If one is never found or *fallthrough* is ``False``, an error message
   will be returned by :class:`ibid.plugins.core.Complain`::

      permission = 'awesome'

      @authorise()
      @match(r'^do\s+awesome\s+things$')
      def method(self, event):
         event.addresponse(u'Yes sir, you are awesome!')

.. function:: periodic([interval=0, config_key=None, initial_delay=60])

   Decorator that runs the method every *interval* seconds, from timer
   events.
   The method won't be called until *initial_delay* seconds have passed
   since startup.

   If *config_key* is set to a string, the :class:`IntOption
   <ibid.config.IntOption>` of that name will be used to set
   ``interval``.
   This is done in :meth:`Processor.setup` so if you override that, be
   sure to call super.

Other Functions
---------------

.. function:: auth_responses(event, permission)

   If the event sender has the *permission* permission, return ``True``.

   If not, the event will be marked as having failed authorisation.
   If no other Processor processes the event, an error message will be
   returned by :class:`ibid.plugins.core.Complain`.

   This is used internally by :meth:`@authorise() <authorise>`, but you
   can call it directly if you need more complex permission handling
   than :meth:`@authorise() <authorise>` allows for.

   When you use this, you should ensure that *permission* is listed in
   :attr:`Processor.permission` or :attr:`Processor.permissions`.

RPC
---

.. class:: RPC

   All methods named with the prefix ``remote_`` will be exposed via
   Ibid's various RPC mechanisms (including the web interface).

   It is common to extend both :class:`Processor` and RPC in the same
   class.
   The handlers can then wrap around the ``remote_`` methods, to provide
   the same features over IM and RPC.

   .. note::

      The RPC code is still experimental and not widely used.
      Don't be surprised if it doesn't work.

.. vi: set et sta sw=3 ts=3:
