from cStringIO import StringIO
import Image
from os import remove
import os.path
import subprocess
from sys import stderr
from tempfile import mkstemp
from urllib2 import urlopen
from zipfile import ZipFile

from aalib import AsciiScreen
from pyfiglet import Figlet

from ibid.config import Option, IntOption
from ibid.plugins import Processor, match
from ibid.utils import file_in_path

"""
Dependencies:
  * libaa (Ubuntu's libaa1-dev package)
  * libcaca (Ubuntu's caca-utils package)
  * Imlib2 (Ubuntu's libimlib2-dev package)
  * pyfiglet (http://sourceforge.net/projects/pyfiglet/)
"""

help = { 'draw'  : u'Retrieve images from the web and render them in ascii-art.',
         'figlet': u'Render text in ascii-art using figlet.' }
class DrawImage(Processor):
    u"""draw <url> [in colour] [width <width>] [height <height>]"""
    feature = 'draw'

    max_filesize = IntOption('max_filesize', 'Only request this many KiB', 200)
    def_height = IntOption('def_height', 'Default height for libaa output', 10)
    max_width = IntOption('max_width', 'Maximum width for ascii output', 60)
    max_height = IntOption('max_width', 'Maximum width for ascii output', 15)
    font_width = IntOption('font_width', 'Font width assumed for output', 6)
    font_height = IntOption('font_height', 'Font height assumed for output', 10)
    img2txt_bin = Option('img2txt_bin', 'libcaca img2txt binary to use', 'img2txt')

    def setup(self):
        if not file_in_path(self.img2txt_bin):
            raise Exception('Cannot locate img2txt executable')

    @match(r'^draw\s+(\S+\.\S+)(\s+in\s+colou?r)?(?:\s+w(?:idth)?\s+(\d+))?(?:\s+h(?:eight)\s+(\d+))?$')
    def draw(self, event, url, colour, width, height):
        f = urlopen(url)

        filesize = int(f.info().getheaders('Content-Length')[0])
        if filesize > self.max_filesize * 1024:
            event.addresponse(u'File too large (limit is %i KiB)', self.max_filesize)
            return

        try:
            ext = os.path.splitext(url)[1]
            image = mkstemp(suffix=ext)[1]
            file = open(image, 'w')
            file.write(f.read())
            file.close()

            try:
                img = Image.open(StringIO(open(image, 'r').read())).convert('L')
            except:
                event.addresponse(u'Cannot understand image format')
                return
            input_width, input_height = img.size[0], img.size[1]

            if width is None and height is None:
                height = self.def_height
                width = height * input_width * self.font_height / input_height / self.font_width
                if width > self.max_width:
                    width = self.max_width
                    height = width * input_height * self.font_width / input_width / self.font_height
                    # Assume def_height <= max_height, so we don't check against max_height
            elif width is None: # only height is set
                height = int(height)
                width = height * input_width * self.font_height / input_height / self.font_width
                if width > self.max_width:
                    # squash the image, rather than returning an error
                    width = self.max_width
                if height > self.max_height:
                    event.addresponse(u"Sorry, I can't draw that tall")
                    return
            elif height is None: # only width is set
                width = int(width)
                height = width * input_height * self.font_width / input_width / self.font_height
                if width > self.max_width:
                    event.addresponse(u"Sorry, I can't draw that wide")
                    return
                if height > self.max_height:
                    # squash the image, rather than returning an error
                    height = self.max_height
            else: # both width and height are set
                width, height = int(width), int(height)
                if width > self.max_width:
                    event.addresponse(u"Sorry, I can't draw that wide")
                    return
                if height > self.max_height:
                    event.addresponse(u"Sorry, I can't draw that tall")
                    return

            if colour is None:
                self.draw_aa(event, image, width, height)
            else:
                self.draw_caca(event, image, width, height)
        finally:
            remove(image)

    def draw_aa(self, event, image, width, height):
        try:
            image = Image.open(StringIO(open(image, 'r').read())).convert('L')
        except:
            event.addresponse(u'Cannot understand image format')
            return
        screen = AsciiScreen(width=width, height=height)
        image = image.resize(screen.virtual_size)
        screen.put_image((0, 0), image)
        event.addresponse(unicode(screen.render()), address=False, conflate=False)

    def draw_caca(self, event, image, width, height):
        from sys import stderr
        process = subprocess.Popen(
            [self.img2txt_bin, '-f', 'irc', '-W', str(width), '-H', str(height), image],
            shell=False, stdout=subprocess.PIPE)
        response, error = process.communicate()
        code = process.wait()
        if code == 0:
            event.addresponse(unicode(response.replace('\r', '')), address=False, conflate=False)
        else:
            event.addresponse(u'Sorry, cannot understand image format')

class WriteFiglet(Processor):
    u"""figlet <text> [in <font>]
    list figlet fonts [from <index>]"""
    feature = 'figlet'

    fonts_zip = Option('fonts_zip', 'Zip file containing figlet fonts', 'data/figlet-fonts.zip')

    def __init__(self, name):
        Processor.__init__(self, name)
        zip = ZipFile(self.fonts_zip)
        self.fonts = sorted(map(lambda n: os.path.splitext(os.path.split(n)[1])[0], zip.namelist()))

    @match(r'^list\s+figlet\s+fonts(?:\s+from\s+(\d+))?$')
    def list_fonts(self, event, index):
        if index is None:
            index = 0
        index = int(index)
        if index >= len(self.fonts):
            event.addresponse(u'I wish I had that many fonts installed')
            return
        event.addresponse(unicode(', '.join(self.fonts[int(index):])))

    @match(r'^figlet\s+(.+?)(\s+in\s+(\S+))?$', 'deaddressed')
    def write(self, event, text, font_phrase, font):
        if font is not None and font not in self.fonts:
            text = '%s%s' % (text, font_phrase)
            font = None
        if font is None:
            font = 'slant'
        self._write(event, text, font)

    def _write(self, event, text, font):
        figlet = Figlet(font=font, zipfile=self.fonts_zip)
        rendered = figlet.renderText(text).split('\n')
        while rendered and rendered[0].strip() == '':
            del rendered[0]
        while rendered and rendered[-1].strip() == '':
            del rendered[-1]
        event.addresponse(unicode('\n'.join(rendered)), address=False, conflate=False)
