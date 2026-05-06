import sounddevice as sd
import numpy as np
import pyglet
from pyglet import window, shapes
import time
from collections import deque
from queue import Queue
from pynput.keyboard import Controller, Key


CHUNK_SIZE = 1024  # Number of audio frames per buffer
RATE = 44100  # Audio sampling rate (HZ)
CHANNELS = 1  # Mono audio


class ChirpDetector:
    """Detects up and down chirps in live audio input. 

    An up chirp is defined as a sudden increase in frequency, 
    while a down chirp is a sudden decrease in frequency over time.
    """

    def __init__(self, min_freq=300, max_freq=3000, chirp_diff=300):
        # Idea for queue from chatgpt
        # Prompt: How can I elegenat exchange data between a callback thread and the main thread in Python?
        self.event_queue = Queue()
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.chirp_diff = chirp_diff
        self.chirp_start_freq = None
        self.chirp_start_time = None
        self.freq_history = deque(maxlen=6)

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)

        data = indata[:, 0]  # mono
        self.detect_live_frequency(data, RATE)

    def detect_live_frequency(self, data, rate):
        # Improved with ChatGPT
        # Prompt: Get most dominant frequency from live audio callback in python
        if np.max(np.abs(data)) < 0.05:
            return None

        # Perform FFT to get frequency spectrum
        win = np.hamming(len(data))
        fft_result = np.fft.rfft(data * win)
        magnitudes = np.abs(fft_result)
        freqs = np.fft.rfftfreq(len(data), 1/rate)

        band = (freqs >= self.min_freq) & (freqs <= self.max_freq)
        band_spectrum = magnitudes[band]
        band_freqs = freqs[band]

        peak = np.argmax(band_spectrum)
        peak_freq = band_freqs[peak]

        self.freq_history.append(peak_freq)
        self.detect_chirp()

    def check_diff(self, freqs):
        for f in freqs:
            for f2 in freqs:
                if abs(f-f2) > 50:
                    return False
        return True

    def detect_chirp(self):
        """Detects up and down chirps based on the frequency history.

        Checks if there is a consistent frequency in the history, 
        and if there is a significant change from the starting frequency.
        If a chirp is detected, it adds an "up" or "down" event to the event queue.
        """

        if len(self.freq_history) < 6:
            return
        check_freqs = self.freq_history.copy()

        # Check if we are already tracking a chirp start
        if self.chirp_start_freq is not None:
            # If it's been too long since the chirp started, reset
            if time.time() - self.chirp_start_time > 0.5:
                self.chirp_start_freq = None
                self.chirp_start_time = None
                self.freq_history.clear()
                return

            # Check if the frequencies in the history are consistent enough to consider it a chirp
            if self.check_diff(check_freqs):
                median = np.median(check_freqs)
                diff = self.chirp_start_freq - median

                if abs(diff) >= self.chirp_diff:
                    self.chirp_start_freq = None
                    if diff < 0:
                        self.event_queue.put("up")
                        print("up chirp detected")
                    if diff > 0:
                        self.event_queue.put("down")
                        print("down chirp detected")
                    return

        if not self.check_diff(check_freqs):
            return

        median = np.median(check_freqs)
        self.chirp_start_freq = median
        self.chirp_start_time = time.time()
        self.freq_history.clear()


class ChirpDemo:
    """ A simple demo with ChirpDetector to control the selection of rectangles on the screen."""

    def __init__(self, window, detector):
        self.height = window.height
        self.width = window.width
        self.detector = detector
        self.keyboard = Controller()
        self.batch = pyglet.graphics.Batch()
        self.rectangles = []
        self.selected = 1
        self.border_size = self.height / 50
        self.create_rects()

    def create_rects(self):
        space = self.height / 5
        height = space / 2
        padding = space / 3
        rect_width = self.width / 3
        x = self.width / 2 - rect_width / 2
        for i in range(3):
            rect = shapes.BorderedRectangle(
                x=x,
                y=(i+1) * space + padding,
                width=rect_width,
                height=height,
                color=(255, 255, 255),
                border_color=(12, 150, 240),
                border=0,
                batch=self.batch
            )
            self.rectangles.append(rect)

        self.rectangles[self.selected].border = self.border_size

    def draw(self):
        self.batch.draw()

    def update(self, t):
        while not self.detector.event_queue.empty():
            event = self.detector.event_queue.get()
            if event == "up":
                self.select_rect(1)
                self.keyboard.press(Key.up)
                self.keyboard.release(Key.up)
            elif event == "down":
                self.select_rect(-1)
                self.keyboard.press(Key.down)
                self.keyboard.release(Key.down)

    def select_rect(self, index):
        select = self.selected + index
        if select > 2 or select < 0:
            return
        self.rectangles[self.selected].border = 0
        self.selected += index
        self.rectangles[self.selected].border = self.border_size


def get_input_decive():
    # print info about audio devices
    print("Available input devices:\n")
    devices = sd.query_devices()

    input_devices = []
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            print(f"{i}: {dev['name']}")
            input_devices.append(i)

    # let user select audio device
    return int(input("\nSelect input device: "))


def main():
    # open audio input stream
    detector = ChirpDetector(300, 3500)
    win = pyglet.window.Window(1280, 800)
    demo = ChirpDemo(win, detector)
    input_device = get_input_decive()

    @win.event
    def on_draw():
        win.clear()
        demo.draw()

    stream = sd.InputStream(
        device=input_device,
        channels=CHANNELS,
        samplerate=RATE,
        blocksize=CHUNK_SIZE,
        callback=detector.audio_callback,
        latency='low'
    )

    stream.start()
    pyglet.clock.schedule_interval(demo.update, 1/30)
    pyglet.app.run()
    stream.stop()
    stream.close()


if __name__ == "__main__":
    main()
