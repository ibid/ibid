:mod:`ibid.event` -- Events
===========================

.. module:: ibid.event
   :synopsis: Events
.. moduleauthor:: Ibid Core Developers

.. class:: Event(source, type)

   Events are at the core of Ibid's workings.
   Every join/part/message seen by a source is dispatched as an
   :class:`ibid.event.Event` to all the plugins to process.
   Then responses are extracted from it and returned to the source.

   :param source: The name of the source that this event relates to.
   :param type: The type of the event, a string of one of the following
      values:

      ``'message'``
         A normal message
      ``'action'``
         An action, the result of a ``/me`` or ``/describe``
      ``'notice'``
         An IRC notice
      ``'state'``
         A state change, such as join, part, online, offline

   Event inherits from :class:`dict` so properties can be get and set
   either as attributes or keys.

   .. attribute:: source

      The *source* string specified at creation.

   .. attribute:: type

      The *type* string specified at creation.

   .. attribute:: responses

      A list of responses that should be returned.

      .. note::

         Rather than appending to this directly, you should use the
         :meth:`addresponse` function.

   .. attribute:: sender

      The sender of the event, a dict with the following keys:

      ``'nick'``
         The user's nickname, as should be used for addressing him/her.
      ``'id'``
         The unique identifier for the user. I.e. jabber address or SILC
         user key hash.
         Used for opening a conversation with a user.
      ``'connection'``
         The unique identifier of connection that the user spoke on.
         Used for addressing the reply to the correct client.

   .. attribute:: complain

      A string, that if present says the :class:`Complain
      <ibid.plugins.core.Complain>` processor should return an error
      message to the sender.

      If set to ``'notauthed'``, the complaint will be about
      insufficient authorisation.

      If set to ``'exception'``, the complaint will be about the bot not
      feeling very well.

   .. attribute:: processed

      A boolean flag indicating that the event has been processed and
      other :class:`Processors <ibid.plugins.Processor>` don't need to
      look at it.

   .. attribute:: session

      A SQLAlchemy :class:`sqlalchemy.orm.session.Session` that can be
      used by a plugin for making queries.

      It will be automatically committed by the dispatcher, but you are
      free to commit in a plugin so you can log a successful commit.

   .. method:: addresponse(response, params={}, processed=True, \*\*kwargs)

      Add a response to an event.

      An event can contain more than one response, they'll be sent as
      separate messages.

      :param response: The unicode response to add, can contain string
         substitutions, which will be provided by *params*.
      :param params: Parameters to substitute into *response*.
         Can either be a single unicode string or a dict of named
         substitutions.
      :param processed: Set :attr:`processed` ``True`` if ``True``.
         Default: ``True``.
      :param source: The source name to direct this reply to.
         Default: :attr:`source`.
      :param target: The user to direct this reply to.
         Default: :attr:`sender['connection'] <sender>`.
      :param address: Boolean flag indicating if the user should be
         addressed when delivering this reply. Default: ``True``.
      :param action: Boolean flag for whether the reply is a message or
         an action. Default: ``False``.
      :param notice: Boolean flag for whether the reply is a message or
         an notice. Default: ``False``.

      Most commonly :meth:`addresponse` is called with a unicode
      parameter for *response* and either a single substitution in
      *params* or multiple, named substitutions.
      However, you can also pass a Boolean value as *response* in which
      case the bot will emit a generic positive or negative response.

      Examples (in public IRC)::

         event.addresponse(True)
         # Sends something like u'user: Okay'
         event.addresponse(False)
         # Sends something like u"user: Shan't"
         event.addresponse(u'Sure')
         # Sends u"user: Sure"
         event.addresponse(u'Jo said "%s"', message)
         # Sends u'user: Jo said "hello"' if message was u'hello'
         event.addresponse(u'%(key)s is %(value)s', {
            'key': u'Spiny Norman',
            'value': u'a Hedgehog',
         })
         # Sends u'user: Spiny Norman is a Hedgehog'
         event.addresponse(u'Look at me', address=False)
         # Sends u'Look at me'
         event.addresponse(u'dances', action=True)
         # Is the equivalent of '/me dances'

.. vi: set et sta sw=3 ts=3:
