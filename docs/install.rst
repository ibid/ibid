.. _installation:

Installation
============

The preferred method of installing a production Ibid is to use the
packages provided by your distro.
Ibid is available in
`Debian <http://packages.qa.debian.org/i/ibid.html>`_ (since squeeze)
and `Ubuntu <http://launchpad.net/ubuntu/+source/ibid>`_ (since Lucid).
Additionally, private backport repositories are available for supported
stable releases of:

* `Debian (lenny) <http://ibid.omnia.za.net/debian/>`_
* `Ubuntu (hardy-karmic) <https://launchpad.net/~ibid-core/+archive/ppa>`_

Installing Ibid :ref:`through your distribution's package-management
system <package-managed>` should give you the least hassles in the long
run [#yourdistro]_.

For plugin-development this will be sufficient, but for :ref:`interaction with the
Ibid development community <contributing>` (i.e. contributing code) or
drastic internal changes, you will probably want to work :ref:`from source
<from-source>` instead.

.. _prerequisites:

Prerequisites
-------------

Python
^^^^^^

You'll need a sane `Python <http://python.org>`_ environment and a few Python
3rd-party packages, described below.

We attempt to support all Python 2.x releases >= 2.4.
However, we'd recommend the most recent stable 2.x release, as Python memory
usage has improved and more recent Python releases have been better tested with
Ibid.
(We have to go out of our way to test with 2.4...)
Python 3.x support is off the cards until our dependencies are 3.x capable.

We expect Ibid to work on most operating systems that can provide Python, but
only develop and test heavily on Debian and Ubuntu Linux.

Python Libraries:
^^^^^^^^^^^^^^^^^

* `Twisted framework <http://twistedmatrix.com/>`_ (core sources)
* Twisted Words (IRC, XMPP)
* `Wokkel <http://wokkel.ik.nu/>`_. (XMPP)
* `SQLAlchemy <http://www.sqlalchemy.org/>`_ 0.5 preferred, 0.4 compatible.
* `ConfigObj <http://www.voidspace.org.uk/python/configobj.html>`_ >= 4.7.0
* `python-dateutil <http://labix.org/python-dateutil>`_
* `SOAPpy <http://pywebsvcs.sourceforge.net/>`_ [#soappy-install]_
* `Setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_

Many core plugins require the following Web scraping & parsing libraries:

* `ElementTree <http://effbot.org/zone/element-index.htm>`_ (only needed for Python 2.4)
* `html5lib <http://code.google.com/p/html5lib/>`_
* `BeautifulSoup <http://www.crummy.com/software/BeautifulSoup/>`_
* `SimpleJSON <http://code.google.com/p/simplejson/>`_ (only needed for Python < 2.6)

Web source and web services:

* `Jinja <http://jinja.pocoo.org/>`_

Other sources:

* SILC: `pysilc <http://www.liquidx.net/pysilc/>`_

There are many non-essential plugins that require other libraries or programs,
they are described in the :ref:`plugin documentation <plugins>`.

Database
^^^^^^^^

Ibid needs a relational database [#db-required]_.
MySQL, PostgreSQL, and SQLite are all supported as first-class citizens.
Using the database-independent backup & restore tool, it is straightforward to
migrate between database engines at any time.

.. _db-setup:

Database Creation
-----------------

By default Ibid will use SQLite, which is a perfectly capable database,
but if you have a MySQL or PostgreSQL server handy, you may prefer to
use it to save some memory or take advantage of the more powerful
feature-set.

If you are using SQLite, you can skip over this section, but for MySQL
or PostgreSQL, you'll need to create a database and DB user before
running ``ibid-setup``.

MySQL
^^^^^

.. highlight:: text

Install MySQL. On Debian/Ubuntu::

   user@box $ sudo aptitude install mysql-server python-mysqldb

You'll be prompted to set a root password for your server. You should
probably do that.

Create a database for your bot::

   user@box $ mysql -u root -p
   Enter password:
   Welcome to the MySQL monitor.
   mysql> CREATE DATABASE joebot CHARSET utf8;
   Query OK, 1 row affected (0.02 sec)
   
   mysql> GRANT ALL PRIVILEGES ON joebot.* TO joebot@localhost IDENTIFIED BY 'mysecret';
   Query OK, 0 rows affected (0.13 sec)
   
   mysql> quit
   Bye

In this example, the database is called ``joebot``, the user ``joebot``
and the password is ``mysecret``, so the DB URL will be::

   mysql://joebot:mysecret@localhost/joebot

PostgreSQL
^^^^^^^^^^

Install PostgreSQL.
You'll also need the ``citext`` contributed module.
On Debian/Ubuntu::

   user@box $ sudo aptitude install postgresql postgresql-contrib python-psycopg2

Create a database for your bot::

   user@box $ sudo -u postgres -i
   postgres@box $ createuser -D -R -S -P joebot
   Enter password for new role:
   Enter it again:
   postgres@box $ createdb -O joebot joebot
   postgres@box $ psql -f /usr/share/postgresql/8.4/contrib/citext.sql joebot
   postgres@box $ logout

In this example, the database is called ``joebot`` and the user
``joebot`` if the password were ``mysecret``, the DB URL would be::

   postgres://joebot:mysecret@localhost/joebot

.. _package-managed:

Package Managed Installation
----------------------------

Add the APT source
^^^^^^^^^^^^^^^^^^

These repositories are only necessary if you are using an old Debian /
Ubuntu release that doesn't include Ibid.

Debian (lenny):
   | ``deb http://ibid.omnia.za.net/debian/ lenny-backports main``
   | GPG Key: `0x5EB879CE
     <http://pgp.surfnet.nl:11371/pks/lookup?search=0x6EC0C1E39DEDE92FC8910161450ED9D55EB879CE&op=index>`_

Ubuntu (pre-lucid):
   | ``deb http://ppa.launchpad.net/ibid-core/ppa/ubuntu karmic main``
   | If you are using a different release to ``karmic``, substitute its name.
   | GPG Key: `0xFD1C44BA
     <http://keyserver.ubuntu.com:11371/pks/lookup?search=0xC2D0F8531BBA37930C0D85E3D59F9E8DFD1C44BA&op=index>`_

You can follow `these instructions
<https://launchpad.net/+help/soyuz/ppa-sources-list.html>`_ or add it from a
terminal like this::

   user@box $ echo deb http://ppa.launchpad.net/ibid-core/ppa/ubuntu `lsb_release -cs` main | sudo tee /etc/apt/sources.list.d/ibid.list
   user@box $ sudo apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 0xFD1C44BA
   user@box $ sudo aptitude update

Install Ibid
^^^^^^^^^^^^

::

   user@box $ sudo aptitude install ibid

Now you should probably create a user for your bot to run as.
While every effort is made to ensure that your bot won't do naughty things, we
can't guarantee that there is no way to exploit it.
If you are feeling adventurous, skip down to creating a bot directory::

   user@box $ sudo adduser --disabled-login ibid

Switch to the bot user::

   user@box $ sudo -u ibid -i
   ibid@box $

If you are going to be using MySQL or PostgreSQL :ref:`set up your
database now <db-setup>`.

Then you'll need to create a directory for your bot to live in::

   ibid@box $ mkdir botdir
   ibid@box $ cd botdir

Now you can install the bot::

   ibid@box $ ibid-setup
   Couldn't load core plugin: botname
   Couldn't load knab plugin: No module named perl
   Couldn't load trac plugin: argument of type 'NoneType' is not iterable
   What would you like to call your bot? joebot
   Please enter the full URL of the database to use, or just press Enter for an SQLite database.
   Database URL: 
   Please enter the details for the primary source. Press Enter for the default option.
   Source name (e.g. freenode, atrum, jabber): freenode
   Server: irc.freenode.net
   Port: 
   Source type (irc or jabber): irc
   Default channels to join (comma separated): #myawesomechannel
   Nick/JID: joeuser
   Password: [my password]
   Account created with admin permissions

.. note::
   This will throw out some harmless errors (about plugins that you don't have
   pre-requisites for).

Load any factpacks you desire (in this case, common greetings)::

   ibid@box $ ibid-factpack greetings.json

Now would be the time to configure your bot.
But for now, let's just get it running::

   ibid@box $ twistd -n ibid

You should see copious debugging output, and the bot should log into your IRC
channel.

.. _from-source:

Installation From Source
------------------------

If you want to do any development, or install from trunk or a specific branch,
you'll need `Bazaar <http://bazaar-vcs.org/>`_ installed.

Firstly, you need the dependencies :ref:`listed above <prerequisites>`.
We recommend a recent release of Debian/Ubuntu Linux, and the instructions are
tailored for such.
If you use something else, you'll have to interpolate.

Install the required python modules.
You can use another DB, but we default to SQLite.
If you are not using Debian/Ubuntu or would prefer to have these
dependencies installed in a virtualenv, you can skip this step::

   user@box $ sudo aptitude install bzr python-configobj python-sqlalchemy \
     python-twisted python-beautifulsoup python-celementtree \
     python-html5lib python-setuptools python-simplejson \
     python-soappy python-jinja python-dateutil python-virtualenv

Create a user to run your bot as::

   user@box $ sudo adduser --disabled-login ibid

Create a virtualenv to install Ibid to::

   user@box $ virtualenv ve

.. note::

   This isn't strictly necessary as Ibid can run out of a source
   checkout for development.
   But for long-term deployments it is sensible to separate the source
   from the botdir.

Checkout the latest version of Ibid (instead of this, you could extract a
source tarball)::

   user@box $ sudo -u ibid -i
   ibid@box $ bzr branch lp:ibid
   ibid@box $ cd ibid

Install Ibid::

   user@box $ . ~/ve/bin/activate
   user@box $ ./setup.py install --no-dependencies

.. note::

   If you didn't install the packages listed in the first step, you'll
   have to remove ``--no-dependencies`` so setuptools can do its magic.

If you are going to be using MySQL or PostgreSQL :ref:`set up your
database now <db-setup>`.

Then you'll need to create a directory for your bot to live in::

   ibid@box $ mkdir ~/botdir
   ibid@box $ cd ~/botdir

Set up your bot::

   ibid@box $ ibid-setup

.. note::
   This will throw out some harmless errors (about plugins that you don't have
   pre-requisites for).

If you haven't created a configuration file, it will ask you to give the bot a
name, and describe the first source.
A source is an IRC network, jabber, or SILC network.

It'll ask you to enter the details of the first administrative account.
Assuming you will be connecting the bot to an IRC server, enter your nick, the
network's name, and a password (e.g. "joebloggs", "freenode", "s3cr3tpass").

Load any factpacks you desire (in this case, common greetings)::

   ibid@box $ ibid-factpack ~/ibid/factpack/greetings.json

Run your bot::

   ibid@box $ twistd -n ibid

.. rubric :: Footnotes

.. [#yourdistro] Your distribution of choice not listed here?
   That's probably because none of the current Ibid developers use it.
   Why not :ref:`chip in <contributing>` and help us package Ibid for you.

.. [#db-required] If you don't need user-accounts (and many other features),
   the database code could be removed.
   It'd probably be quite a bit of work, though.

.. [#soappy-install] SOAPpy can be hard to install, so we have debian
   packages and eggs to help. ``setup.py`` knows where to look.

.. vi: set et sta sw=3 ts=3:
