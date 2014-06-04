import numpy 

smooth_start = numpy.linspace(0, 1, 10)
smooth_end = numpy.linspace(1, 0, 10)

def norm_smooth(buf, count=10):
    ''' Normalizes the buffer to unity. Offsets to 0 RMS, and applies
        a smoothing to the front and end of the buffer as a primitive
        pop-supression '''

    res = numpy.zeros_like(buf)
    res[:] = buf - numpy.sqrt(numpy.mean(buf * buf))

    scalar = max(numpy.max(res), -numpy.min(res))
    # numpy doesn't raise on a divide-by-zero, only warns and produces nan's
    if abs(scalar) < 1e-12:
        return buf

    res /= scalar
    res[0:count] *= smooth_start
    res[-count:] *= smooth_end
    return res

class SequencerPage:
    def __init__(self, ncols):
        self.state = [(0, 0)] * ncols
        self.cache = [None] * ncols
        self.buf = None

    def setup(self, variations, buflen, instruments):
        self.variations = variations
        self.buflen = buflen
        self.instruments = instruments

    def update(self, col, val):
        self.cache[col] = None
        self.buf = None
        # We're essentially decoding the incoming value
        # Pick off the refbits'th least signficant bits 
        # The minus 1 is because the incoming value is 1-indexed, while
        # the arrays of references and instruments are 0-indexed.
        # Internally store representations 0-indexed
        refval = val & 0b111
        instrval = val >> 3
        self.state[col] = (refval, instrval)

        # BIG TODO: Something or another

    def __put_chunk(self, col, chunk):
        if chunk is None: return
        start_frame = int(float(col) * self.buflen / len(self.state))

        # If the sample we want to write overflows the buffer, wrap around
        overflow = start_frame + len(chunk) - len(self.buf)
        if overflow > 0:
            self.buf[start_frame: -1] += chunk[0: len(chunk) - overflow - 1]
        else:
            self.buf[start_frame:start_frame + len(chunk)] += chunk

    def __render_instr(self, i):
        if self.instruments is not None:
            if i in range(len(self.instruments)):
                return self.instruments[i]
        return None

    def __render_ref(self, p):
        if self.variations is not None:
            if p in range(len(self.variations)):
                return self.variations[p].render()
        return None

    def render(self, force=False):
        self.buf = numpy.zeros(self.buflen)

        for col, (refval, instrval) in enumerate(self.state):
            self.__put_chunk(col, self.__render_ref(refval - 1))
            self.__put_chunk(col, self.__render_instr(instrval - 1))

        self.buf = norm_smooth(self.buf)
        return self.buf

