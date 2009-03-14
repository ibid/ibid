from datetime import datetime
from urllib import urlencode
from BeautifulSoup import BeautifulSoup

import urllib2
import re
import htmlentitydefs
import logging

import ibid
from ibid.plugins import Processor, match, handler
from ibid.config import Option

help = {'delicious': u'Saves URLs seen in channel to configured delicious account'}
log  = logging.getLogger('plugins.delicious')

class Grab(Processor):

    addressed = False
    processed = True
    delname   = Option('delname', 'delicious account name')
    delpwd    = Option('delpwd',  'delicious account password')

    @match(r'((?:\S+://|(?:www|ftp)\.)\S+|\S+\.(?:com|org|net|za)\S*)')
    def grab(self, event, url):
        self._add_post(self.delname,self.delpwd,url,event.sender['connection'],event.sender['nick'],event.channel)

    def _add_post(self,username,password,url=None,connection=None,nick=None,channel=None):
        "Posts a URL to delicious.com"
        if url == None:
            return
        if url.find('://') == -1:
            if url.lower().startswith('ftp'):
                url = 'ftp://%s' % url
            else:
                url = 'http://%s' % url

        date  = datetime.now()
        title = self._get_title(url)

        connection_body = re.split('!', connection)
        if len(connection_body) == 1:
            connection_body.append(connection)
        obfusc = re.sub('@\S+?\.', '^', connection_body[1])
        tags = nick + " " + obfusc

        data = {
            'url' : url,
            'description' : title,
            'tags' : tags,
            'replace' : 'yes',
            'dt' : date,
            }

        try:
            self._set_auth(username,password)
            posturl = "https://api.del.icio.us/v1/posts/add?"+urlencode(data)
            resp = urllib2.urlopen(posturl).read()
            if resp.find('done') > 0:
                log.info(u"Successfully posted url %s posted in channel %s by nick %s at time %s", url, channel, nick, date)
            else:
                log.error(u"Error posting url %s: %s", url, response)

        except urllib2.URLError, e:
            log.error(u"Error posting url %s: %s", url, e.message)
        except Exception, e:
            log.error(u"Error posting url %s: %s", url, e.message)

    def _get_title(self,url):
        "Gets the title of a page"
        try:
            soup = BeautifulSoup(urllib2.urlopen(url))
            title = str(soup.title.string)
             ## doing a de_entity results in > 'ascii' codec can't encode character u'\xab' etc.
             ## leaving this code here in case someone works out how to get urllib2 to post unicode?
             #final_title = self._de_entity(title)
            return title
        except Exception, e:
            log.error(u"Error determining the title for url %s: %s", url, e.message)
            return url

    def _set_auth(self,username,password):
        "Provides HTTP authentication on username and password"
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password('del.icio.us API', 'https://api.del.icio.us', username, password)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

    def _de_entity(self,text):
        "Remove HTML entities, and replace with their characters"
        replace = lambda match: unichr(int(match.group(1)))
        text = re.sub("&#(\d+);", replace, text)

        replace = lambda match: unichr(htmlentitydefs.name2codepoint[match.group(1)])
        text = re.sub("&(\w+);", replace, text)
        return text


# vi: set et sta sw=4 ts=4:
