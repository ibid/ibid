import re

from ibid.plugins import Processor, match

help = {}

help["morse"] = u"Translates messages into and out of morse code."

class Morse(Processor):
    u"""morse (text|morsecode)"""
    feature = 'morse'

    @match(r'^morse\s*(.*)$')
    def morse(self, event, message):
     
        table = {
                'A': ".-",
                'B': "-...",
                'C': "-.-.",
                'D': "-..",
                'E': ".",
                'F': "..-.",
                'G': "--.",
                'H': "....",
                'I': "..",
                'J': ".---",
                'K': "-.-",
                'L': ".-..",
                'M': "--",
                'N': "-.",
                'O': "---",
                'P': ".--.",
                'Q': "--.-",
                'R': ".-.",
                'S': "...",
                'T': "-",
                'U': "..-",
                'V': "...-",
                'W': ".--",
                'X': "-..-",
                'Y': "-.--",
                'Z': "--..",
                '0': "-----",
                '1': ".----",
                '2': "..---",
                '3': "...--",
                '4': "....-",
                '5': ".....",
                '6': "-....",
                '7': "--...",
                '8': "---..",
                '9': "----.",
                ' ': " ",
                '.': ".-.-.-",
                ',': "--..--",
                '?': "..--..",
                ':': "---...",
                ';': "-.-.-.",
                '-': "-....-",
                '_': "..--.-",
                '"': ".-..-.",
                "'": ".----.",
                '/': "-..-.",
                '(': "-.--.",
                ')': "-.--.-",
                '=': "-...-",
        }

        if "message_raw" in event:
            message = re.match(r'^.*?morse\s+(.+)$', event.message_raw).group(1)

        def text2morse(text):
            return u" ".join(table.get(c.upper(), c) for c in text)
        
        def morse2text(morse):
            rtable = dict((v, k) for k, v in table.items())
            toks = morse.split(u' ')
            return u"".join(rtable.get(t, u' ') for t in toks)

        if message.replace(u'-', u'').replace(u'.', u'').strip() == u'':
            event.addresponse(u'Decodes as %s', morse2text(message))
        else:
            event.addresponse(u'Encodes as %s', text2morse(message))

# vi: set et sta sw=4 ts=4:
