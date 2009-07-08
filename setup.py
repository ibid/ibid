#!/usr/bin/env python

from setuptools import setup

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
    install_requires=[
        'Twisted',
        'Twisted_Words',
        'Twisted_Web',
        'Twisted_Mail',
        'SQLAlchemy>=0.4.6',
        'wokkel==0.4',
        'jinja',
        'SOAPpy',
        'simplejson',
        'html5lib',
        'BeautifulSoup',
    ],
    dependency_links=['http://wokkel.ik.nu/downloads'],
    packages=['ibid', 'tracibid', 'lib', 'twisted', 'contrib', 'factpacks'],
    entry_points={
        'trac.plugins': ['tracibid = tracibid.notifier'],
    },
    scripts=['scripts/ibid', 'scripts/ibid-setup', 'scripts/ibid-factpack', 'scripts/ibid_pb', 'scripts/ibid_import', 'scripts/ibid.tac', 'scripts/ibid-plugin'],
    include_package_data=True,
    zip_safe=False,
)

# vi: set et sta sw=4 ts=4:
