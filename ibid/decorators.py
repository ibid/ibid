import re

def addressed(function):
	@message
	def new(self, event):
		if 'addressed' not in event or not event['addressed']:
			return
		return function(self, event)
	return new

def notprocessed(function):
	def new(self, event):
		if 'processed' in event and event['processed']:
			return
		return function(self, event)
	return new

def message(function):
	def new(self, event):
		if 'msg' not in event:
			return
		return function(self, event)
	return new

def match(regex):
	pattern = re.compile(regex, re.I)
	def wrap(function):
		@message
		def new(self, event):
			matches = pattern.search(event['msg'])
			if not matches:
				return
			return function(self, event, *matches.groups())
		return new
	return wrap

def addressedmessage(pattern=None):
	def wrap(function):
		@addressed
		@notprocessed
		def new(self, query):
			return function(self, query)
		if pattern:
			return match(pattern)(new)
		else:
			return new
	return wrap
