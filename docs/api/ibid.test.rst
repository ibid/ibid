:mod:`ibid.test` -- Ibid Testing
================================

.. module:: ibid.test
   :synopsis: Ibid Testing
.. moduleauthor:: Ibid Core Developers

End-to-end testing
------------------

.. class:: PluginTestCase
    A subclass of Twisted Trial's :class`unittest.TestCase
    <twisted.trial.unittest.TestCase`. It sets up an environment much like a
    running Ibid including a clean database, and loads the specified plugins.

    The clean database is a SQLite database at ``ibid/test/test.db`` (which needs to
    be updated when the schema changes). The tests also use the config at
    ``ibid/test/test.ini``

    .. attribute:: load

        List: strings naming plugins to be loaded before running tests.

        Default: ``[]``

    .. attribute:: noload

        List: strings naming plugins *not* to be loaded.

        Default: ``[]``

    .. attribute:: load_base

        Boolean: whether to load a small set of base plugins (namely, admin and core).

        Default: ``True``

    .. attribute:: load_configured

        Boolean: load all configured modules (excluding :attr:`noload`).

        Default: if :attr:`load` is empty, ``True``; otherwise, ``False``.

    .. attribute:: username

        String: the default username/nick in events created by the
        :func:`make_event` method.

        Default: ``u'user'``

    .. attribute:: public

        Boolean: whether or not the events created by :func:`make_event` are
        public.

        Default: ``False``
