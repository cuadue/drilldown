import time
import numpy

from pymonome import monome

import audio

BPM = 20
ROWS, COLS = 8, 8
PAGES = 1

class Sequencer:
    def __init__(self, ncols, next_page, refbits=2):
        pass

    def update(self, col, val):
        # Pick off the refbits'th least signficant bits 
        refval = val & ~(~0 << refbits)

        # Pick off the remaining bits
        instrval = val >> refbits




class Drilldown(monome.Monome):
    def __init__(self, audio_server, instruments, address):
        monome.Monome.__init__(self, address)
        self.instruments = instruments
        self.state = [[0 for n in range(COLS)] for i in range(PAGES)]
        self.aserver = audio_server
        self.current_page = 0
        
        #self.seqs = [Sequencer


    def grid_key(self, x, y, s):
        if not s:
            return # for now, we ignore the key-up events

        # Update the state by toggling the y'th bit on page x
        self.state[self.current_page][x] ^= 1 << y
        #self.aserver.write_buf(self.render())
        self.update_led_state()

    def render(self):
        pass


    def update_led_state(self):
        # We store state in column-major order so we have to transpose into
        # row-major order to suit /grid/led/map
        page = self.state[self.current_page]
        self.led_map(0, 0, [sum(((col >> nrow) & 1) << ncol 
                                for ncol, col in enumerate(page))
                            for nrow in range(ROWS)])


aserver = audio.AudioServer(BPM)
aserver.start()
instruments = [aserver.oscillator(f) for f in 
                                [400, 500, 737, 903, 1088, 1330, 1818, 2000]]

app = Drilldown(aserver, instruments, monome.find_any_monome())
app.start()

app.led_all(0)
try:
    while True:
        for i in range(8):
            time.sleep(1.0/20)
except KeyboardInterrupt:
    app.led_all(0)
    app.close()

