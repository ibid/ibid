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
		'SQLAlchemy>=0.4.4',
		'wokkel>=0.4',
		'ConfigObj>=4.5.3',
		'validate>=0.3.2',
	],
	packages=find_packages(exclude=['lib']),
	scripts=['ibid.tac', 'ibid.py', 'populatedb.py'],
	include_package_data=True,
	package_data={
		'': ['*.ini'],
	},
	exclude_package_data={
		'lib': ['*'],
	}
)
