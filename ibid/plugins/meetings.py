from datetime import datetime, timedelta
import logging
from os import chmod, makedirs
from os.path import dirname, expanduser, join
import re
from urllib import quote
from xmlrpclib import ServerProxy

from dateutil.parser import parse
from dateutil.tz import tzlocal, tzutc
from jinja import Environment, PackageLoader

import ibid
from ibid.compat import json
from ibid.config import BoolOption, IntOption, Option
from ibid.plugins import Processor, match, authorise
from ibid.utils import format_date, plural

help = {}
log = logging.getLogger('plugins.meetings')

templates = Environment(loader=PackageLoader('ibid', 'templates'))
meetings = {}

help['meeting'] = u'Take minutes of an IRC Meeting'
class Meeting(Processor):
    u"""
    (start | end) meeting [about <title>]
    I am <True Name>
    topic <topic>
    (agreed | idea | accepted | rejected) <statement>
    minutes so far
    meeting title is <title>
    """
    feature = 'meeting'
    permission = u'chairmeeting'

    formats = Option('formats', u'Formats to log to. '
            u'Requires templates of the name meeting/minutes.format',
            ('json', 'txt', 'html'))
    logfile = Option('logfile', u'File name for meeting logs. '
            u'Can contain substitutions: source, channel, date, format',
            'logs/meetings/%(source)s-%(channel)s-%(date)s.%(format)s')
    logurl = Option('logurl', u'Public URL for meeting logs. '
            u'Can contain substitutions: source, channel, date, format '
            u'If unset, will use a pastebin.',
            None)
    date_format = Option('date_format', 'Format to substitute %(date)s with',
            '%Y-%m-%d-%H-%M-%S')

    file_mode = IntOption('file_mode', u'File Permissions mode, in octal', 644)

    @authorise
    @match(r'^start\s+meeting(?:\s+about\s+(.+))?$')
    def start_meeting(self, event, title):
        if not event.public:
            event.addresponse(u'Sorry, must be done in public')
            return
        if (event.source, event.channel) in meetings:
            event.addresponse(u'Sorry, meeting in progress.')
            return
        meeting = {
            'starttime': event.time,
            'convenor': event.sender['nick'],
            'source': event.source,
            'channel': ibid.sources[event.source]
                .logging_name(event.channel),
            'title': title,
            'attendees': {},
            'minutes': [{
                'time': event.time,
                'type': 'started',
                'subject': None,
                'nick': event.sender['nick'],
            }],
            'log': [],
        }
        meetings[(event.source, event.channel)] = meeting

        event.addresponse(u'gets out his memo-pad and cracks his knuckles',
                action=True)

    @match(r'^i\s+am\s+(.+)$')
    def ident(self, event, name):
        if not event.public or (event.source, event.channel) not in meetings:
            return

        meeting = meetings[(event.source, event.channel)]
        meeting['attendees'][event.sender['nick']] = name

        event.addresponse(True)

    @authorise
    @match(r'^(topic|idea|agreed|accepted|rejected)\s+(.+)$')
    def identify(self, event, action, subject):
        if not event.public or (event.source, event.channel) not in meetings:
            return

        action = action.lower()

        meeting = meetings[(event.source, event.channel)]
        meeting['minutes'].append({
            'time': event.time,
            'type': action,
            'subject': subject,
            'nick': event.sender['nick'],
        })

        if action == 'topic':
            message = u'Current Topic: %s'
        elif action == 'idea':
            message = u'Idea recorded: %s'
        elif action == 'agreed':
            message = u'Agreed: %s'
        elif action == 'accepted':
            message = u'Accepted: %s'
        elif action == 'rejected':
            message = u'Rejected: %s'
        event.addresponse(message, subject, address=False)

    @authorise
    @match(r'^meeting\s+title\s+is\s+(.+)$')
    def set_title(self, event, title):
        if not event.public:
            event.addresponse(u'Sorry, must be done in public')
            return
        if (event.source, event.channel) not in meetings:
            event.addresponse(u'Sorry, no meeting in progress.')
            return
        meeting = meetings[(event.source, event.channel)]
        meeting['title'] = title
        event.addresponse(True)

    @match(r'^minutes(?:\s+(?:so\s+far|please))?$')
    def write_minutes(self, event):
        if not event.public:
            event.addresponse(u'Sorry, must be done in public')
            return
        if (event.source, event.channel) not in meetings:
            event.addresponse(u'Sorry, no meeting in progress.')
            return
        meeting = meetings[(event.source, event.channel)]
        meeting['attendees'].update((e['nick'], None) for e in meeting['log']
                if e['nick'] not in meeting['attendees']
                and e['nick'] != ibid.config['botname'])

        render_to = set()
        if self.logurl is None:
            render_to.add('txt')
        render_to.update(self.formats)
        minutes = {}
        for format in render_to:
            if format == 'json':
                class DTJSONEncoder(json.JSONEncoder):
                    def default(self, o):
                        if isinstance(o, datetime):
                            return o.strftime('%Y-%m-%dT%H:%M:%SZ')
                        return json.JSONEncoder.default(self, o)
                minutes[format] = json.dumps(meeting, cls=DTJSONEncoder,
                        indent=2)
            else:
                template = templates.get_template('meetings/minutes.' + format)
                minutes[format] = template.render(meeting=meeting) \
                        .encode('utf-8')

            filename = self.logfile % {
                'source': event.source.replace('/', '-'),
                'channel': meeting['channel'].replace('/', '-'),
                'date': meeting['starttime'].strftime(self.date_format),
                'format': format,
            }
            filename = join(ibid.options['base'], expanduser(filename))
            try:
                makedirs(dirname(filename))
            except OSError, e:
                if e.errno != 17:
                    raise e
            f = open(filename, 'w+')
            chmod(filename, int(str(self.file_mode), 8))
            f.write(minutes[format])
            f.close()

        if self.logurl is None:
            pastebin = ServerProxy('http://paste.pocoo.org/xmlrpc/',
                    allow_none=True)
            id = pastebin.pastes.newPaste(None, minutes['txt'], None, '',
                    'text/plain', False)

            url = u'http://paste.pocoo.org/show/' + id
        elif u'%(format)s' not in self.logurl:
            # Content Negotiation
            url = self.logurl % {
                'source': quote(event.source.replace('/', '-')),
                'channel': quote(meeting['channel'].replace('/', '-')),
                'date': quote(meeting['starttime'].strftime(self.date_format)),
            }
        else:
            url = u' :: '.join(u'%s: %s' % (format, self.logurl % {
                'source': quote(event.source.replace('/', '-')),
                'channel': quote(meeting['channel'].replace('/', '-')),
                'date': quote(meeting['starttime'].strftime(self.date_format)),
                'format': quote(format),
            }) for format in self.formats)

        event.addresponse(u'Minutes available at %s', url, address=False)

    @authorise
    @match(r'^end\s+meeting$')
    def end_meeting(self, event):
        if not event.public:
            event.addresponse(u'Sorry, must be done in public')
            return
        if (event.source, event.channel) not in meetings:
            event.addresponse(u'Sorry, no meeting in progress.')
            return
        meeting = meetings[(event.source, event.channel)]

        meeting['endtime'] = event.time
        meeting['log'].append({
            'nick': event.sender['nick'],
            'type': event.type,
            'message': event.message['raw'],
            'time': event.time,
        })
        meeting['minutes'].append({
            'time': event.time,
            'type': 'ended',
            'subject': None,
            'nick': event.sender['nick'],
        })

        event.addresponse(u'Meeting Ended', address=False)
        self.write_minutes(event)
        del meetings[(event.source, event.channel)]

class MeetingLogger(Processor):
    addressed = False
    processed = True
    priority = 1900
    feature = 'meeting'

    def process(self, event):
        if 'channel' in event and 'source' in event \
                and (event.source, event.channel) in meetings:
            meeting = meetings[(event.source, event.channel)]
            message = event.message
            if isinstance(message, dict):
                message = message['raw']
            meeting['log'].append({
                'nick': event.sender['nick'],
                'type': event.type,
                'message': message,
                'time': event.time,
            })
            for response in event.responses:
                type = 'message'
                if response.get('action', False):
                    type = 'action'
                elif response.get('notice', False):
                    type = 'notice'

                meeting['log'].append({
                    'nick': ibid.config['botname'],
                    'type': type,
                    'message': response['reply'],
                    'time': event.time,
                })

help['poll'] = u'Does a quick poll of channel members'
class Poll(Processor):
    u"""
    [secret] poll on <topic> [until <time>] vote <option> [or <option>]...
    vote (<id> | <option>) [on <topic>]
    end poll
    """
    feature = 'poll'
    permission = u'chairmeeting'

    polls = {}

    date_utc = BoolOption('date_utc', u'Interpret poll end times as UTC', False)
    poll_time = IntOption('poll_time', u'Default poll length', 5 * 60)

    @authorise
    @match(r'^(secret\s+)?(?:poll|ballot)\s+on\s+(.+?)\s+'
            r'(?:until\s+(.+?)\s+)?vote\s+(.+\sor\s.+)$')
    def start_poll(self, event, secret, topic, end, options):
        if not event.public:
            event.addresponse(u'Sorry, must be done in public')
            return

        if (event.source, event.channel) in self.polls:
            event.addresponse(u'Sorry, poll on %s in progress.',
                    self.polls[(event.source, event.channel)].topic)
            return

        class PollContainer(object):
            pass
        poll = PollContainer()
        self.polls[(event.source, event.channel)] = poll

        poll.secret = secret is not None
        if end is None:
            poll.end = event.time + timedelta(seconds=self.poll_time)
        else:
            poll.end = parse(end)
            if poll.end.tzinfo is None and not self.date_utc:
                poll.end = poll.end.replace(tzinfo=tzlocal())
            if poll.end.tzinfo is not None:
                poll.end = poll.end.astimezone(tzutc()).replace(tzinfo=None)
        if poll.end < event.time:
            event.addresponse(u"I can't end a poll in the past")
            return

        poll.topic = topic
        poll.options = re.split(r'\s+or\s+', options)
        poll.lower_options = [o.lower() for o in poll.options]
        poll.votes = {}

        event.addresponse(
            u'You heard that, voting has begun. '
            u'The polls close at %(end)s. '
            u'%(private)s'
            u'The Options Are:', {
                'private': poll.secret
                    and u'You may vote in public or private. '
                    or u'',
                'end': format_date(poll.end),
            }, address=False)

        for i, o in enumerate(poll.options):
            event.addresponse(u'%(id)i: %(option)s', {
                'id': i + 1,
                'option': o,
            }, address=False)

        delay = poll.end - event.time
        poll.delayed_call = ibid.dispatcher.call_later(
                delay.days * 86400 + delay.seconds,
                self.end_poll, event)

    def locate_poll(self, event, selection, topic):
        "Attempt to find which poll the user is voting in"
        if event.public:
            if (event.source, event.channel) in self.polls:
                return self.polls[(event.source, event.channel)]
        else:
            if topic:
                polls = [p for p in self.polls.iteritems()
                        if p.topic.lower() == topic.lower()]
                if len(polls) == 1:
                    return polls[0]
            polls = [self.polls[p] for p in self.polls.iterkeys()
                    if p[0] == event.source]
            if len(polls) == 1:
                return polls[0]
            elif len(polls) > 1:
                if not selection.isdigit():
                    possibles = [p for p in polls
                            if selection.lower() in p.lower_options]
                    if len(possibles) == 1:
                        return possibles[0]
                event.addresponse(u'Sorry, I have more than one poll open. '
                        u'Please say "vote %s on <topic>"', selection)
                return
        event.addresponse(u'Sorry, no poll in progress')

    @match(r'^vote\s+(?:for\s+)?(.+?)(?:\s+on\s+(.+))?$')
    def vote(self, event, selection, topic):
        poll = self.locate_poll(event, selection, topic)
        log.debug(u'Poll: %s', repr(poll))
        if poll is None:
            return

        if selection.isdigit() and int(selection) > 0 \
                and int(selection) <= len(poll.options):
            selection = int(selection) - 1
        else:
            try:
                selection = poll.lower_options.index(selection)
            except ValueError:
                event.addresponse(
                    u"Sorry, I don't know of such an option for %s",
                    poll.topic)
                return
        poll.votes[event.identity] = selection
        if not event.public:
            event.addresponse(
                u'Your vote on %(topic)s has been registered as %(option)s', {
                    'topic': poll.topic,
                    'option': poll.options[selection],
            })
        else:
            event.processed = True

    @match('^end\s+poll$')
    @authorise
    def end_poll(self, event):
        if not event.public:
            event.addresponse(u'Sorry, must be done in public')
            return

        if (event.source, event.channel) not in self.polls:
            event.addresponse(u'Sorry, no poll in progress.')
            return

        poll = self.polls.pop((event.source, event.channel))
        if poll.delayed_call.active():
            poll.delayed_call.cancel()

        votes = [[poll.options[i], 0]
                for i in range(len(poll.options))]
        for vote in poll.votes.itervalues():
            votes[vote][1] += 1
        votes.sort(reverse=True, key=lambda x: x[1])
        event.addresponse(u'The polls are closed. Totals:', address=False)

        position = (1, votes[0][1])
        for o, v in votes:
            if v < position[1]:
                position = (position[0] + 1, v)
            event.addresponse(
                    u'%(position)i: %(option)s - %(votes)i %(word)s', {
                        'position': position[0],
                        'option': o,
                        'votes': v,
                        'word': plural(v, u'vote', u'votes'),
                }, address=False)

# vi: set et sta sw=4 ts=4:
