:mod:`ibid.config` -- Configuration Files
=========================================

.. module:: ibid.config
   :synopsis: Configuration File Interface
.. moduleauthor:: Ibid Core Developers

This module handles Ibid's configuration file and provides helper
functions for accessing configuration from sources and plugins.

Helper Functions
----------------

.. class:: Option(name, description, default=None)

   A unicode string configuration item.

   :param name: The configuration key
   :param description: A human-readable description for the
      configuration item.
   :param default: The default value, if not specified in the
      configuration file.

   If created as an attribute to a :class:`ibid.plugins.Processor` or
   :class:`ibid.source.IbidSourceFactory`, it will retrieve the value of
   ``plugins``.\ *plugin*.\ *name* or ``sources``.\ *source*.\ *name*.

   This is also the base class for other Options.

   Example::

      class Secret(Processor):
         password = Option('password', 'Secret Password', 's3cr3t')

   Assuming that processor is in the ``secret`` plugin, the
   configuration item could be provided as:

   .. code-block:: ini

      [plugins]
         [[secret]]
            password = blue

.. class:: BoolOption(name, description, default=None)

   A boolean configuration item.

   Usage is identical to :class:`Option`.

.. class:: IntOption(name, description, default=None)

   A integer configuration item.

   Usage is identical to :class:`Option`.

.. class:: FloatOption(name, description, default=None)

   A floating-point configuration item.

   Usage is identical to :class:`Option`.

.. class:: ListOption(name, description, default=None)

   A list configuration item.
   Values will be unicode strings.

   Usage is identical to :class:`Option`.

.. class:: DictOption(name, description, default=None)

   A dictionary configuration item.
   Keys and values will be unicode strings.

   Usage is identical to :class:`Option`.

Core Functions
--------------

.. function:: FileConfig(filename)

   Parses *filename* and returns a configuration tree.

.. vi: set et sta sw=3 ts=3:
