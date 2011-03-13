#!/usr/bin/env python
# Copyright (c) 2008-2011, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from sys import version_info, argv

from setuptools import setup

install_requires=[
    'BeautifulSoup',
    'configobj>=4.7.0',
    'dnspython',
    'feedparser',
    'html2text',
    'html5lib',
    'jinja',
    'pyopenssl',
    'PyStemmer',
    'python-dateutil',
    'SOAPpy',
    'SQLAlchemy>=0.5,<0.6a', # Works with >=0.4.6 except on OS X
    'Twisted',
    'wokkel>=0.6.3',
]

if version_info[0] == 2 and version_info[1] < 6:
    install_requires.append('simplejson')
if version_info[0] == 2 and version_info[1] < 5:
    install_requires.append('cElementTree')
    install_requires.append('pysqlite')

if argv[1:] == ['install', '--no-dependencies']:
    argv.pop()
    install_requires = None

setup(
    name='Ibid',
    version='0.2.0dev',
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
        'memory': ['objgraph'],
        'asciiart': ['python-aalib'],
    },
    packages=['ibid', 'tracibid', 'twisted', 'contrib', 'factpacks'],
    entry_points={
        'trac.plugins': ['tracibid = tracibid.notifier'],
    },
    scripts=[
        'scripts/ibid',
        'scripts/ibid-db',
        'scripts/ibid-factpack',
        'scripts/ibid-knab-import',
        'scripts/ibid-memgraph',
        'scripts/ibid-objgraph',
        'scripts/ibid-pb-client',
        'scripts/ibid-plugin',
        'scripts/ibid-setup',
        'scripts/ibid.tac',
    ],

    include_package_data=True,
    zip_safe=False,
)

# vi: set et sta sw=4 ts=4:
