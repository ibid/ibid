from setuptools import setup, find_packages

setup(
	name='Ibid',
	version='0.1',
	description='A modular, extensible IRC/IM bot',
	url='http://ibid.omnia.za.net/',
	keywords='bot irc jabber',
	py_modules=['ibid'],
	setup_requires=['setuptools_bzr'],
	install_requires=[
		'SQLAlchemy>=0.5',
	],
	packages=find_packages(),
	scripts=['ibid.tac', 'ibid.py', 'populatedb.py'],
	include_package_data=True,
)
