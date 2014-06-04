import time
import numpy

from pymonome import monome

import audio
from sequencer import SequencerPage

BPM = 5
ROWS, COLS = 8, 8
DURATIONS, VARIS = 8, 8

class Drilldown(monome.Monome):
    def __init__(self, audio_server, instruments, address):
        monome.Monome.__init__(self, address)
        self.state = [[[0] * COLS] * VARIS] * DURATIONS

        self.aserver = audio_server
        self.selected_dur = 0
        self.selected_var = 0

        self.pages = [[SequencerPage(COLS) 
                        for v in range(VARIS)] 
                          for d in range(DURATIONS)]

        for i in range(DURATIONS):
            bufsize = int(audio.RATE * 60 / BPM / (2 ** (3 * i)))
            # Kind of annoying to have a second init routine: this data
            # structure is self-referential but non-recursive.
            next_pages = self.pages[i+1] if i+1 < DURATIONS else []
            for p in self.pages[i]:
                p.setup(next_pages, bufsize, instruments)

        self.root_page = SequencerPage(1)
        self.root_page.setup(self.pages[0], audio.RATE * 60 / BPM, None)
        # We always want to play the root page
        self.root_page.state = [(1,0)]

    def grid_key(self, x, y, s):
        if not s: return # for now, ignore the key-up events

        if y == 0:
            self.selected_dur = x
        elif y == 1:
            self.selected_var = x

        page = self.pages[self.selected_dur][self.selected_var]
        state = self.state[self.selected_dur][self.selected_var] 

        if y > 1:
            state[x] ^= 1 << (y - 2)
            # We consume the first two bits for page and state selection.
            page.update(x, state[x])

        self.aserver.write_buf(self.root_page.render(force=True))

        # Update LED state.
        # State is stored in in column-major order so we have to transpose into
        # row-major order to suit /grid/led/map
        m = ([1 << self.selected_dur, 1 << self.selected_var] + 
                            [sum(((col >> nrow) & 1) << ncol 
                                for ncol, col in enumerate(state))
                            for nrow in range(ROWS - 2)])

        self.led_map(0, 0, m)

aserver = audio.AudioServer(BPM)
aserver.start()

instruments = [audio.load_wav('samples/%d.wav' % p) for p in range(1, 8)]

app = Drilldown(aserver, instruments, monome.find_any_monome())
app.start()

app.led_all(0)
try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    app.led_all(0)
    app.close()

