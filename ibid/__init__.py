import ibid.core

sources = {}
config = {}
dispatcher = None
processors = []
reloader = None

def reload_reloader():
	reload(ibid.core)
	new_reloader = ibid.core.Reloader()
	ibid.reloader = new_reloader
