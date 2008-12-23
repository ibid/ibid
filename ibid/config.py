class Config(dict):

	def __getattr__(self, name):
		return self[name]

	def __setattr__(self, name, value):
		self[name] = value

class StaticConfig(Config):

	def __init__(self):
		local = {'name': 'local', 'type': 'irc', 'server': 'localhost', 'nick': 'Ibid', 'channels': ['#cocoontest']}
		atrum = {'type': 'irc', 'server': 'za.atrum.org', 'nick': 'Ibid', 'channels': ['#ibid']}
		jabber = {'type': 'jabber', 'server': 'jabber.org', 'ssl': True, 'jid': 'ibidbot@jabber.org/source', 'password': 'ibiddev'}
		myjabber = {'name': 'jabber', 'type': 'jabber', 'server': 'gorven.za.net', 'ssl': True, 'jid': 'ibid@gorven.za.net/source', 'password': 'z1VdLdxgunupGSju'}
		telnet = {'type': 'telnet', 'port': 3000}
		timer = {'type': 'timer', 'step': 5}

		self.name = 'Ibid'
		self.sources = {'local': local, 'atrum': atrum, 'jabber': jabber, 'telnet': telnet, 'clock': timer}
		self.processors = ['core.Addressed', 'irc.Actions', 'core.Ignore', 'admin.ListModules', 'admin.LoadModules', 'basic.Greet', 'info.DateTime', 'basic.SayDo', 'test.Delay', 'basic.Complain', 'core.Responses', 'log.Log']
		self.modules = {
				'core.Addressed': {'names': ['Ibid', 'bot', 'ant']}, 
				'core.Ignore': {'ignore': ['NickServ']}, 
				'ping': {'type': 'dbus.Proxy', 'bus_name': 'org.ibid.module.Ping', 'object_path': '/org/ibid/module/Ping', 'pattern': '^ping$'},
				'log.Log': {'logfile' : '/tmp/ibid.log'}}
