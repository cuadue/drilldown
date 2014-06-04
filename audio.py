import threading
import Queue
import time
import pyaudio
import numpy

import aifc, wave, struct

STREAM_BUF_SIZE = 512
CHANNELS = 1
RATE = 44100
PI = numpy.pi
PI2 = 2 * PI

# Listen: You were trying to convert samples to analog time and back into
# samples, and somehow gain meaning from this. No. You started with samples and
# you will end with samples, and this is the beauty of synthesis: as long as
# you can feed the buffer fast enough, your sound will come out at the correct
# pitch and at the correct time.  So, don't render time. You already have a
# hardware metronome that you can multiply or divide however you see fit, and
# other than that you'll hear something that, even if it's not what you
# desired, will be at least technically "correct".

def str2nparray(s, samplewidth, nframes, nchannels, endianness):
    ''' Converts the given string of bytes into a numpy array.
        str - the string to be converted
        samplewidth - sample width in bytes
        nframes - number of frames
        nchannels - number of channels '''

    types = {2:'h', 4:'i', 8:'l'}
    fmt = endianness + ("{0}".format(nframes * nchannels) + 
                    types.get(samplewidth))
    samples = struct.unpack(fmt, s)
    res = numpy.asarray(samples, numpy.float32)

    scalar = max(numpy.max(res), -numpy.min(res))
    return res / (scalar if abs(scalar) > 1e-12 else 1)

def _load_sample(path, mod, endianness):
    f = mod.open(path, 'r')
    result = f.readframes(f.getnframes())
    f.close()
    return str2nparray(result, f.getsampwidth(), f.getnframes(),
                       f.getnchannels(), endianness=endianness)

def load_wav(path):
    return _load_sample(path, wave, '<')

def load_aiff(path):
    return _load_sample(path, aifc, '<')

def sine(freq, dur):
    return numpy.sin(PI2 * freq * numpy.linspace(0, dur * RATE, dur * RATE))

class RingBuffer:
    def __init__(self, buf, end):
        self.end = end
        self.buf = buf

    def next_frames(self, frames):
        start = self.end
        end = (self.end + frames) % len(self.buf)
        self.end = end
        if start > end:
            result = numpy.concatenate((self.buf[start:], self.buf[:end]))
        else:
            result = self.buf[start:end]

        # If this assertion fails, Bad Things (tm) will happen to your ears.
        assert(len(result) == frames)
        return result


class AudioServer(threading.Thread):
    def __init__(self, bpm):
        super(AudioServer, self).__init__()
        self.daemon = True
        self.buf_queue = Queue.Queue()

    def write_buf(self, buf):
        b = numpy.zeros(len(buf))
        b[:] = buf # Make a deep copy of the input buffer
        self.buf_queue.put(b)

    def run(self):
        p = pyaudio.PyAudio()
        stream = p.open(format = pyaudio.paFloat32,
                        channels = CHANNELS,
                        rate = RATE,
                        output = True,
                        frames_per_buffer = STREAM_BUF_SIZE)

        __buf = None
        while True:
            try:
                # Fetch the newest loop if one exists in the queue.  We can't
                # wait for another sample to be available because the actual
                # audio server is hungry and we have to keep it well fed
                samples = self.buf_queue.get_nowait()
                __buf = RingBuffer(samples, __buf.end if __buf else 0)
            except Queue.Empty:
                pass

            if __buf is None:
                # But if we have nothing to feed the buffer, then we must wait
                # for some hapless prey to fall into it's gaping trap
                time.sleep(0.001)
            else:
                # We want to keep the buffer full at all times to trade one
                # kind of latency for another: faster response from user to
                # buffer, slower from buffer to output
                chunk = __buf.next_frames(stream.get_write_available())
                if chunk is not None:
                    stream.write(chunk.astype(numpy.float32).tostring())

