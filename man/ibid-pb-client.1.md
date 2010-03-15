% IBID-PB-CLIENT(1) Ibid Multi-protocol Bot | Ibid 0.1
% Stefano Rivera
% March 2010

# NAME

ibid-pb-client - RPC Client for Ibid

# SYNOPSIS

**ibid-pb-client** [*options*...] **message** *message*  
**ibid-pb-client** [*options*...] **plugin** *feature* *method* [*parameter*...]  
**ibid-pb-client** **-h**

# DESCRIPTION

This utility is for passing events to a running Ibid bot, or executing
RPC-exposed functions remotely.

It communicates with the **pb** source on the Ibid.

*message* is a text message as could be sent to the bot by an IM source.
The message is processed normally by the bot.

*feature* is the name of the feature to invoke exposed method **method** on,
directly.
*parameter*s are passed directly to the method.
They can be specified positionally or by key, using the same syntax as Python:
_key_**=**_value_.
They may be encoded in JSON, if not valid JSON they will be treated as
strings.

The output is a JSON-encoded response.

# OPTIONS

**-s** *SERVER*, **--server**=*SERVER*
:	Connect to the Ibid running on *SERVER*, by default it connects to
	*localhost*.

**-p** *PORT*, **--port**=*PORT*
:	Connect to the **pb** source running on port *PORT*, by default 8789.

**-h**, **--help**
:	Show a help message and exit.

# SEE ALSO

`ibid` (1),
http://ibid.omnia.za.net/
