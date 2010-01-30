#!/usr/bin/env python
# Copyright (c) 2008-2010 Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from sys import version_info, argv

from setuptools import setup

install_requires=[
    'dnspython',
    'feedparser',
    'wokkel',
    'SOAPpy',
    'pyopenssl',
    'pysqlite',
    'python-dateutil',
    'jinja',
    'html5lib',
    'BeautifulSoup',
    'SQLAlchemy>=0.5', # Works with >=0.4.6 except on OS X
    'Twisted',
]

if version_info[0] == 2 and version_info[1] < 6:
    install_requires.append('simplejson')
if version_info[0] == 2 and version_info[1] < 5:
    install_requires.append('cElementTree')

if argv[1:] == ['install', '--no-dependencies']:
    argv.pop()
    install_requires = None

setup(
    name='Ibid',
    version='0.0',
    description='Multi-protocol general purpose chat bot',
    url='http://ibid.omnia.za.net/',
    keywords='chat bot irc jabber twisted messaging',
    author='Ibid Developers',
    author_email='ibid@omnia.za.net',
    license='MIT',
    py_modules=['ibid'],
    install_requires=install_requires,
    extras_require = {
        'imdb': ['imdbpy'],
    },
    dependency_links=[
        'http://ibid.omnia.za.net/eggs/',
        'http://wokkel.ik.nu/downloads',
    ],
    packages=['ibid', 'tracibid', 'twisted', 'contrib', 'factpacks'],
    entry_points={
        'trac.plugins': ['tracibid = tracibid.notifier'],
    },
    scripts=[
        'scripts/ibid',
        'scripts/ibid-db',
        'scripts/ibid-plugin',
        'scripts/ibid-setup',
        'scripts/ibid-factpack',
        'scripts/ibid-pb-client',
        'scripts/ibid-knab-import',
        'scripts/ibid.tac',
    ],

    include_package_data=True,
    zip_safe=False,
)

# vi: set et sta sw=4 ts=4:
