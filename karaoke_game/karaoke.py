import sounddevice as sd
import numpy as np
import pyqtgraph as pg
import pyglet
from pyglet import window, shapes
from mido import MidiFile

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024  # Number of audio frames per buffer
RATE = 44100  # Audio sampling rate (HZ)
CHANNELS = 1  # Mono audio


class MidiVisual:
    def __init__(self, notes, width, height):
        self.notes = notes
        self.width = width
        self.height = height

        self.freq_high = self.get_max_freq() + 200      #For padding to top of screen

        self.pixel_per_seconds = 200
        self.note_height = 30
        self.batch = pyglet.graphics.Batch()
        self.rectangles = []

        self.create_rectangles()

    def get_max_freq(self):
        max_freq = max(note["freq"] for note in self.notes)
        return max_freq

    def map_freq_to_y(self, freq):
        y = (freq * self.height) / self.freq_high
        return y

    def create_rectangles(self):
        for note in self.notes:
            x = note["start"] * self.pixel_per_seconds
            y = self.map_freq_to_y(note["freq"])
            w = note["duration"] * self.pixel_per_seconds
            h = self.note_height

            rect = shapes.Rectangle(
                x=x,
                y=y,
                width=w,
                height=h,
                color=(173, 212, 237),
                batch=self.batch
            )
            rect.opacity = 90
            self.rectangles.append(rect)

    def draw(self):
        self.batch.draw()


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


def get_karaoke_song():
    # print info about audio devices
    print("Available karaoke songs:\n")
    songs = {'Ode and die Freude': 'freude',
             'Von den blauen Bergen kommen wir': 'berge'}
    for i, (song_name, song_file) in enumerate(songs.items()):
        print(f"{i}: {song_name}")

    song = int(input("\nSelect a song: "))
    song_items = list(songs.items())
    song_name, song_file = song_items[song]
    return song_name, song_file


# Convert midi note to frequency https://inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
def midi_note_to_freq(note):
    return 440.0 * (2 ** ((note - 69) / 12))


def read_midi(midi_file):
    """
    Reads a MIDI file and extracts note information.

    Made with the support of ChatGPT
    Prompt: parse MIDI files in Python using mido with overlapping notes and store them in in a dict
    """

    notes = []
    active_note = {}
    time_ellapsed = 0
    for msg in MidiFile(midi_file):
        time_ellapsed += msg.time

        if msg.type == 'note_on':
            active_note[msg.note] = time_ellapsed

        if msg.type == 'note_off':
            start = active_note[msg.note]
            notes.append({
                "note": msg.note,
                "freq": midi_note_to_freq(msg.note),
                "start": start,
                "end": time_ellapsed,
                "duration": time_ellapsed - start
            })
    return notes


def audio_callback(indata, frames, time, status):
    if status:
        print(status)

    data = indata[:, 0]  # mono
    detect_live_frequency(data, RATE)


def detect_live_frequency(data, rate):
    """
    Detects the dominant frequency in the given audio data and prints it.

    Made with the help of ChatGPT - Prompt "get freqeuncy from live audio in python using np.rfft"
    """

    if np.max(np.abs(data)) < 0.05:
        return None

    fft_result = np.fft.rfft(data)
    magnitudes = np.abs(fft_result)

    freqs = np.fft.rfftfreq(len(data), 1/rate)
    valid = (freqs >= 80) & (freqs <= 1000)

    relevant_freqs = freqs[valid]
    relevant_magnitudes = magnitudes[valid]

    peak_index = np.argmax(relevant_magnitudes)
    peak_freq = relevant_freqs[peak_index]

    if peak_freq is not None:
        print(peak_freq)


window = pyglet.window.Window(1000, 600)

input_device = get_input_decive()
song_name, song_file = get_karaoke_song()
notes = read_midi(f"read_midi/{song_file}.mid")
visual = MidiVisual(notes, window.width, window.height)


@window.event
def on_draw():
    window.clear()
    visual.draw()


# open audio input stream
stream = sd.InputStream(
    device=input_device,
    channels=CHANNELS,
    samplerate=RATE,
    blocksize=CHUNK_SIZE,
    callback=audio_callback,
    latency='low'
)

stream.start()
pyglet.app.run()
stream.stop()
stream.close()
