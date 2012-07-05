import time
import numpy

from pymonome import monome

import audio
from sequencer import SequencerPage

BPM = 20
ROWS, COLS = 8, 8
PAGES, VARIS = 2, 2

class Drilldown(monome.Monome):
    def __init__(self, audio_server, instruments, address):
        monome.Monome.__init__(self, address)
        self.state = [[0 for n in range(COLS)] for i in range(PAGES)]
        self.aserver = audio_server
        self.current_page = 0
        self.current_variation = 0

        self.pages = [[SequencerPage(COLS) for v in range(VARIS)] 
                       for i in range(PAGES)]

        # The minus one is because the last page has no references to next
        for i in range(PAGES):
            bufsize = int(audio.RATE * 60 / BPM / 2 ** i)
            # Kind of annoying to have a second init routine: this data
            # structure is self-referential but non-recursive.
            next_pages = self.pages[i+1] if i+1 < PAGES else []
            for p in self.pages[i]:
                p.setup(next_pages, bufsize, instruments)

        self.root_page = SequencerPage(1)
        self.root_page.setup(self.pages[0], audio.RATE * 60 / BPM, None)
        # We always want to play the root page
        self.root_page.state[0] = (0, -1)

    def grid_key(self, x, y, s):
        if not s: return # for now, ignore the key-up events

        # Update the state by toggling the y'th bit in column x
        self.state[self.current_page][x] ^= 1 << y
        # The first 2 bits are reference bits and are binary encoded
        # The remaining 6 bits can take on 6 values
        self.state[self.current_page][x] &= (1 << y) | 0b11
        
        # Send that freshly updated column to the sequencer
        page = self.pages[self.current_page][self.current_variation]
        page.update(x, self.state[self.current_page][x])

        buf = self.root_page.render(force=True)
        if buf is not None:
            self.aserver.write_buf(buf)
        else:
            print 'Nothing to play!'
        self.update_led_state()

    def update_led_state(self):
        # We store state in column-major order so we have to transpose into
        # row-major order to suit /grid/led/map
        page = self.state[self.current_page]
        self.led_map(0, 0, [sum(((col >> nrow) & 1) << ncol 
                                for ncol, col in enumerate(page))
                            for nrow in range(ROWS)])


aserver = audio.AudioServer(BPM)
aserver.start()
synth = audio.Synthesizer(aserver)
instruments = [synth.sine(f, 0.1) for f in 
                                [400, 500, 737, 903, 1088, 1330, 1818, 2000]]

app = Drilldown(aserver, instruments, monome.find_any_monome())
app.start()

app.led_all(0)
try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    app.led_all(0)
    app.close()

