import threading
import time
import pyaudio
import numpy
from copy import deepcopy

STREAM_BUF_SIZE = 512
CHANNELS = 1
RATE = 44100
BPM = 100
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

class RingBuffer:
    def __init__(self, buf):
        self.end = 0
        self.buf = buf

    def next_frames(self, frames):
        # Make a ring buffer
        if not frames: return

        start = self.end
        end = (self.end + frames) % len(self.buf)
        self.end = end
        if start > end:
            result = numpy.concatenate((self.buf[start:], self.buf[:end]))
        else:
            result = self.buf[start:end]

        assert(len(result) == frames)
        return result


class AudioServer(threading.Thread):
    def __init__(self, bpm):
        super(AudioServer, self).__init__()
        self.daemon = True
        self.__buf = None
        self.__buflock = threading.Lock()

        self.t = numpy.linspace(0, 1, RATE  * 60 / BPM)

    def oscillator(self, freq, vec_ang_fn=numpy.sin):
        return vec_ang_fn(numpy.pi * 2 * self.t)

    def write_buf(self, buf):
        self.__buflock.acquire()
        b = numpy.zeros(len(buf))
        b[:] = buf
        self.__buf = RingBuffer(b)
        self.__buflock.release()
        
    def run(self):
        p = pyaudio.PyAudio()
        stream = p.open(format = pyaudio.paFloat32,
                        channels = CHANNELS,
                        rate = RATE,
                        output = True,
                        frames_per_buffer = STREAM_BUF_SIZE)
        try:
            while True:
                # We want to keep the buffer full at all times to trade one kind of
                # latency for another: faster response from user to buffer,
                # slower from buffer to output
                
                if self.__buf is None:
                    continue

                chunk = self.__buf.next_frames(stream.get_write_available())
                if chunk is not None:
                    stream.write(chunk.astype(numpy.float32).tostring(),
                                 exception_on_underflow=True)
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

