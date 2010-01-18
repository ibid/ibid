from twisted.trial import unittest

from ibid.plugins import urlgrab

class TestURLGrabber(unittest.TestCase):

    def setUp(self):
        self.grab = urlgrab.Grab(u'testplugin')

    good_grabs = [
        (u'google.com', u'google.com'),
        (u'http://foo.bar', u'http://foo.bar'),
        (u'aoeuoeu <www.jar.com>', u'www.jar.com'),
        (u'aoeuoeu <www.jar.com> def', u'www.jar.com'),
        (u'<www.jar.com>', u'www.jar.com'),
        (u'so bar http://foo.bar/baz to jo', u'http://foo.bar/baz'),
        (u"'http://bar.com'", u'http://bar.com'),
        (u'Thingie boo.com/a eue', u'boo.com/a'),
        (u'joe (www.google.com) says foo', u'www.google.com'),
        (u'http://www.example.net/blog/2008/11/09/debugging-python-regular-expressions/',
            u'http://www.example.net/blog/2008/11/09/debugging-python-regular-expressions/'),
        (u'aoeu http://www.example.net/blog/2008/11/09/debugging-python-regular-expressions/ aoeu',
            u'http://www.example.net/blog/2008/11/09/debugging-python-regular-expressions/'),
        (u'aoeu http://www.example.net/blog/2008/11/09/debugging-python-regular-expressions/. aoeu',
            u'http://www.example.net/blog/2008/11/09/debugging-python-regular-expressions/'),
        (u'http://www.example.net/blog/2008/11/09/debugging-python-regular-expressions/.',
            u'http://www.example.net/blog/2008/11/09/debugging-python-regular-expressions/'),
        (u'ouoe <http://www.example.net/blog/2008/11/09/debugging-python-regular-expressions/> aoeuao',
            u'http://www.example.net/blog/2008/11/09/debugging-python-regular-expressions/'),
        # We accept that the following are non-optimal
        (u'http://en.example.org/wiki/Python_(programming_language)',
            u'http://en.example.org/wiki/Python_(programming_language'),
        (u'Python <http://en.example.org/wiki/Python_(programming_language)> is a lekker language',
            u'http://en.example.org/wiki/Python_(programming_language'),
        (u'Python <URL:http://en.example.org/wiki/Python_(programming_language)> is a lekker language',
            u'http://en.example.org/wiki/Python_(programming_language'),
        (u'Spinach - Wikipedia, the free encyclopedia <http://en.wikipedia.org/wiki/Spinach>, WHFoods: Spinach',
            u'http://en.wikipedia.org/wiki/Spinach'),
        (u"<http://mylifeisaverage.com/story.php?id=293529>: Today, I noticed MLIA'S mode is the mathematical term for average. MLIA is smarter than me. MLIA",
            u'http://mylifeisaverage.com/story.php?id=293529'),
    ]

    def test_good_grabs(self):
        for input, url in self.good_grabs:
            m = self.grab.grab.im_func.pattern.search(input)
            self.assertEqual(m.group(1), url, input)

    bad_grabs = [
        u'joe@bar.com',
        u'x joe@google.com',
        u'<joe@bar.com>',
        u'joe@bar.za.net',
        u'File "/usr/lib/python2.5/httplib.py", line 866, in request',
    ]

    def test_bad_grabs(self):
        for input in self.bad_grabs:
            m = self.grab.grab.im_func.pattern.search(input)
            self.assertEqual(m, None, input)

# vi: set et sta sw=4 ts=4:
