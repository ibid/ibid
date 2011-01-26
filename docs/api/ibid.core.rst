:mod:`ibid.core` -- Ibid Core
=============================

.. module:: ibid.core
   :synopsis: Ibid Core
.. moduleauthor:: Ibid Core Developers

This module contains Ibid's startup code, plugin, source, config, and DB
loading as well as the Event dispatcher.

Dispatcher
----------

.. function:: process(event, log)

   This function takes *event* and passes it to the
   :meth:`process() <ibid.plugins.Processor.process>` function in
   each processor, in order of increasing :attr:`priority
   <ibid.plugins.Processor.priority>`. Messages are logged on the logger
   *log*.

   After each :class:`Processor <ibid.plugins.Processor>`, any
   unclean SQLAlchemy sessions are committed and exceptions logged.

.. class:: Dispatcher

   The Ibid :class:`Event <ibid.event.Event>` dispatcher.

   .. method:: call_later(delay, callable, oldevent, \*args, \*\*kwargs)

      Run *callable* after *delay* seconds, passing it *oldevent* and
      *\*args* and *\*kwargs*.

      Returns a :class:`twisted.internet.base.DelayedCall`.

      Can be used in plugins instead of blocking in sleep.

Internal Functions
^^^^^^^^^^^^^^^^^^

   .. method:: _process(event)

      The core of the dispatcher, must be called from a worker thread.

      This function takes *event* and passes it to the
      :func:`process() <ibid.core.process>` function.
      Any responses attached to *event* are then dispatched to their
      destination sources.

   .. method:: send(response)

      Dispatches *response* to the appropriate source.

   .. method:: dispatch(event)

      Called by sources to dispatch *event*.
      Calls :meth:`_process`, deferred to a thread, and returns the
      :class:`twisted.internet.defer.Deferred`.

   .. method:: delayed_call(callable, event, \*args, \*\*kwargs)

      The method called by :meth:`call_later`, in a thread, to call
      *callable*, then :meth:`_process` on *event*.

   .. method:: delayed_response(event)

      Dispatches responses from :meth:`delayed_call`.

Reloader
--------

.. class:: Reloader

   The center of Ibid's bootstrap process, the reloader loads plugins
   and processors.
   They can be reloaded at any time.

   .. method:: run()

      Boostrap Ibid and run the reactor.

   .. method:: reload_dispatcher()

      Reload the Ibid dispatcher.

   .. method:: load_source(name, [service])

      Load source of name *name*, setting the service parent to
      *service*.

   .. method:: load_sources([service])

      Load all enabled sources, setting the service parents to
      *service*.

      Sources can be disabled by setting the configuration key
      *service*.``disabled = True``.

   .. method:: unload_source(name)

      Unload source of name *name*.

   .. method:: reload_source(name)

      Re-load source of name *name*.

   .. method:: load_processors([load, noload, autoload])

      Load all enabled processors, according to the rules in
      :meth:`load_processor`.

      *load* specifies the plugins to force loading, *noload* plugins to
      skip loading, and *autoload* whether to load everything by
      default.
      If these parameters are not supplied or are ``None``, they will be
      looked up as configuration keys in the ``plugins`` block.

   .. method:: load_processor(name, [noload, load, load_all=False,
      noload_all=False])

      Load the plugin of name *name*.
      Individual Processors can be disabled by listing them in *noload*.
      If they are marked with
      :attr:`~ibid.plugins.Processor.autoload` = ``False``, then
      they are skipped unless listed in *load* or *load_all* is
      ``True``.

   .. method:: unload_processor(name).

      Unload plugin of name *name*.

   .. method:: reload_databases()

      Reload the Databases.

   .. method:: reload_auth()

      Reload the :mod:`ibid.auth`.

   .. method:: reload_config()

      Notify all processors of a configuration reload, by calling
      :meth:`setup() <ibid.plugins.Processor.setup>`.

Databases
---------

.. function:: regexp(pattern, item)

   Regular Expression function for SQLite.

.. function:: sqlite_creator(database)

   Connect to a SQLite database, with regular expression support, thanks
   to :func:`regexp`.

.. class:: DatabaseManager(check_schema_versions=True)

   The DatabaseManager is responsible for loading databases (usually
   only one, ``'ibid'``), and is a dict of database to
   :class:`sqlalchemy.orm.scoping.ScopedSession`\ s.

   .. method:: load(name)

      Load the database of name *name*.

      Echoing is configured by ``debugging.sqlalchemy_echo``.

      Databases are configured as sanely as possible:

      * All databases are brought up in a UTF-8 mode, with UTC timezone.
      * MySQL has the default engine set to InnoDB and ANSI mode enabled.

.. vi: set et sta sw=3 ts=3:
