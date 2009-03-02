from ibid.plugins import Processor, match

help = {}

help["morse"] = u"Translates messages into and out of morse code."

class Morse(Processor):
    u"""morse (text|morsecode)"""
    feature = 'morse'

    @match(r'^morse\s+(.+)$')
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


        def text2morse(text):
            return u" ".join(table.get(c.upper(), c) for c in text)
        
        def morse2text(morse):
            rtable = dict((v, k) for k, v in table.items())
            toks = morse.split(' ')
            return u" ".join(rtable.get(t, t) for t in toks)

        if message.replace('-', '').replace('.', '').isspace():
            event.addresponse(morse2text(message))
        else:
            event.addresponse(text2morse(message))
