.. _contributing:

Contributing
============

.. _bug_reporting:

Bug Reporting
-------------

Please report any bugs in `the Launchpad tracker
<https://bugs.launchpad.net/ibid>`_.
(Oh, and check for existing ones that match your problem first.)

Good bug reports describe the problem, include the message to the bot
that caused the bug, and any logging information / exceptions from
``ibid.log``.


Submitting Patches
------------------

Want to go one step further, and fix your bug or add a new feature.
We welcome contributions from everyone.
The best way to get a patch merged quickly is to follow the same
development process as the Ibid developers:

#. If you don't have one, `create a Launchpad account
   <https://launchpad.net/+login>`_ and configure Bazaar to use it.

#. If there isn't a bug in the tracker for this change, file one.
   It motivates the change.

#. Mark the bug as *In Progress*, assigned to you.

#. Take a branch of Ibid trunk (See :ref:`bzr-guide` if you are new to
   Bazaar)::

      user@box $ bzr branch lp:ibid description-1234

   ``description`` is a two or three-word hyphen-separated description
   of the branch, ``1234`` is the Launchpad bug number.

#. Fix your bug in this branch, following the :ref:`style-guidelines`.
   See also :ref:`dev-instance`.

#. Link the commit that fixes the bug to the launchpad bug::

      user@box $ bzr commit --fixes lp:1234

#. Test that the fix works as expected and doesn't introduce any new
   bugs. ``pyflakes`` can find syntax errors you missed.

#. Run the test-cases::

      user@box $ PYTHONPATH=. trial ibid

#. Push the branch to Launchpad::

      user@box $ bzr push lp:~yourname/ibid/description-1234

#. Find the branch `on Launchpad <https://code.launchpad.net/ibid>`_ and
   propose it for merging into the Ibid trunk.


.. _style-guidelines:

Style Guidelines
----------------

Writing code that matches the Ibid style will lead to a consistent code
base thus happy developers.

* Follow `PEP 8 <http://www.python.org/dev/peps/pep-0008>`_, where it
  makes sense.

* 4 space indentation.

* Single quotes are preferred to double, where sensible.

Sources
^^^^^^^

* Follow `Twisted style
  <http://twistedmatrix.com/trac/browser/trunk/doc/core/development/policy/coding-standard.xhtml?format=raw>`_.

Plugins
^^^^^^^

* All features should have help and usage strings.

* Try to code for the general case, rather than your specific problem.
  ``Option`` configurables are handy for this, but don't bother making
  things that will never be changed configurable (i.e. static API
  endpoints).

* Use ``event.addresponse``'s string formatting abilities where
  possible.
  This will aid in future translation.

* Any changes to database schema should have upgrade-rules included for
  painless upgrade by users.

.. _bzr-guide:

Bazaar for Ibid Developers
--------------------------

You'll want a non-ancient version (>=1.6) of Bazaar (check your
distribution's backport repository), and a Launchpad account.

If you've never used Bazaar before, read `Bazaar in five minutes
<http://doc.bazaar-vcs.org/latest/en/mini-tutorial/index.html>`_.

Configure Bazaar to know who you are::

   ~ $ bzr whoami "Arthur Pewtey <apewtey@example.com>"
   ~ $ bzr launchpad-login apewtey

Make a Bazaar shared repository to contain all your Ibid branches::

   ~ $ mkdir ~/code/ibid
   ~ $ cd ~/code/ibid
   ~/code/ibid $ bzr init-repo --1.6 .

Check out Ibid trunk::

   ~/code/ibid $ bzr checkout lp:ibid trunk

When you wish to create a new branch::

   ~/code/ibid $ bzr update trunk
   ~/code/ibid $ bzr branch trunk feature-1234

If you want to easily push this to Launchpad, create a
``~/.bazaar/locations.conf`` with the following contents::

   [/home/apewtey/code/ibid]
   pull_location = lp:~apewtey/ibid/
   pull_location:policy = appendpath
   push_location = lp:~apewtey/ibid/
   push_location:policy = appendpath
   public_branch = lp:~apewtey/ibid/
   public_branch:policy = appendpath

That will allow you to push your branch to
``lp:~apewtey/ibid/feature-1234`` by typing::

   ~/code/ibid/feature-1234 $ bzr push

To delete a branch, you can simply ``rm -rf`` it.

See also:

* `Launchpad code hosting documentation
  <https://help.launchpad.net/Code>`_
* `Using Bazaar with Launchpad
  <http://doc.bazaar-vcs.org/latest/en/tutorials/using_bazaar_with_launchpad.html>`_
* `Bazaar User Guide
  <http://doc.bazaar-vcs.org/latest/en/user-guide/>`_
* `Bazaar Reference
  <http://doc.bazaar-vcs.org/latest/en/user-reference/index.html>`_


.. _dev-instance:

Running a Development Ibid
--------------------------

A full-blown Ibid install is overkill for development and debugging
cycles.

Ibid source contains a developer-oriented ``ibid.ini`` in the root
directory.
This uses SQLite and connects to a South African IRC server.
If you wish to change it, either remember not to commit this file to
your branch, or override settings in ``local.ini``, which is ignored by
Bazaar.

Ibid can be simply run out of a checkout directory::

   ~/code/ibid/feature-1234 $ export PYTHONPATH=.
   ~/code/ibid/feature-1234 $ scripts/ibid-setup

If you won't need an administrative account, you can hit ``^D`` and
avoid setting one up.

Test a specific plugin::

   ~/code/ibid/feature-1234 $ scripts/ibid-plugin pluginname

Test with all plugins loaded::

   ~/code/ibid/feature-1234 $ scripts/ibid-plugin -c

.. note::
   Not all plugin features will work in the ``ibid-plugin`` environment.
   In particular, anything relying on source-interaction or timed
   callbacks (such as many of the games).
   Also, all permissions are granted.

If ``ibid-plugin`` isn't sufficient for your debugging needs, you can
launch a normal Ibid by running::

   ~/code/ibid/feature-1234 $ twistd -n ibid


.. vi: set et sta sw=3 ts=3:
