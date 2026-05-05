import sounddevice as sd
import numpy as np
import pyglet
from pyglet import window, shapes
from pyglet.window import key
from mido import MidiFile
import time
from collections import deque

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 2048  # Number of audio frames per buffer
RATE = 44100  # Audio sampling rate (HZ)
CHANNELS = 1  # Mono audio

MIDI_DIR = "read_midi"
WAVE_DIR = "wave"
BACKGROUND_PATH = "karaoke_game/background.jpg"


class MidiVisual:
    def __init__(self, notes, width, height):
        self.notes = notes
        self.width = width
        self.height = height

        self.freq_high = self.get_max_freq()
        self.freq_low = self.get_min_freq()
        self.pixel_per_seconds = 200
        self.note_height = 30
        self.batch = pyglet.graphics.Batch()
        self.rectangles = []

        self.create_rectangles()

    def get_max_freq(self):
        max_freq = max(note["freq"] for note in self.notes)
        return max_freq

    def get_min_freq(self):
        min_freq = min(note["freq"] for note in self.notes)
        return min_freq

    def map_freq_to_y(self, freq):
        """Maps a frequency value to coordinate based on the range of frequencies in the song."""

        display_height = self.height * 0.4
        padding = (self.height - display_height) / 2
        y = ((freq - self.freq_low) * display_height) / \
            (self.freq_high - self.freq_low)
        return y + padding

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
                color=(255, 255, 255),
                batch=self.batch
            )
            rect.opacity = 90
            self.rectangles.append(rect)

    def draw(self):
        self.batch.draw()


class Game:
    def __init__(self, song_name, detector, window):
        self.notes = read_midi(f"{MIDI_DIR}/{song_name}.mid")
        self.visuals = MidiVisual(self.notes, window.width, window.height)
        self.detector = detector
        self.player = pyglet.media.Player()
        self.music = pyglet.media.load(
            f"{WAVE_DIR}/{song_name}.wav", streaming=False)

        self.cursor = shapes.Line(
            x=0,
            y=0,
            x2=0,
            y2=window.height,
            thickness=3,
            color=(255, 0, 0)
        )

        self.playing = False
        self.start_time = None
        self.voice_batch = pyglet.graphics.Batch()
        self.voice_visuals = []
        self.score = 0
        self.score_label = pyglet.text.Label(
            text="Score:",
            font_size=36,
            x=window.width - window.width / 8,
            y=window.height - window.height / 15
        )
        self.pitch_info = pyglet.text.Label(
            text="",
            font_size=45,
            weight='extrabold',
            x=window.width / 2 - (window.width / 12),
            y=window.height / 2 - (window.height / 15)
        )
        self.countdown = None
        self.countdown_label = pyglet.text.Label(
            text="",
            font_size=200,
            weight='extrabold',
            x=(window.width / 2) - (window.width / 30),
            y=window.height / 2 - (window.height / 15)
        )

    def update_countdown(self, t):
        if self.countdown is not None:
            self.countdown -= 1
            if self.countdown > 0:
                self.countdown_label.text = str(self.countdown)
            else:
                self.countdown_label.text = "GO"
                pyglet.clock.unschedule(self.update_countdown)
                pyglet.clock.schedule_once(self.start_music, 0.2)

    def start_music(self, t):
        self.playing = True
        self.start_time = time.time()
        self.player.queue(self.music)
        self.player.play()
        self.countdown = None

    def start(self):
        if self.playing or self.countdown is not None:
            return

        self.countdown = 3
        self.countdown_label.text = str(self.countdown)
        pyglet.clock.schedule_interval(self.update_countdown, 1)

    def get_song_time(self):
        if not self.playing:
            return 0
        return time.time() - self.start_time

    def draw(self):
        self.visuals.draw()
        self.cursor.draw()
        self.voice_batch.draw()
        self.score_label.draw()
        self.pitch_info.draw()
        if self.countdown is not None:
            self.countdown_label.draw()

    def get_current_note(self, songtime):
        for note in self.notes:
            if note["start"] <= songtime <= note["end"]:
                return note
        return None

    def create_voice_point(self, x, freq, opacity=100):
        r = self.visuals.note_height / 2
        y = self.visuals.map_freq_to_y(freq) + r

        point = shapes.Circle(
            x=x,
            y=y,
            radius=r,
            batch=self.voice_batch,
            color=(2, 147, 250),
        )
        point.opacity = opacity
        self.voice_visuals.append(point)

    def calculate_points(self, diff):

        if diff < 50:
            return 60
        if diff < 100:
            return 30
        if diff < 150:
            return 10
        return 0

    def get_pitch_info(self, diff):
        if diff > 50:
            return "you're to high"
        if diff < -50:
            return "your're to low"

    def update(self, t):
        if not self.playing:
            return
        song_time = self.get_song_time()
        x = song_time * self.visuals.pixel_per_seconds
        self.cursor.x = x
        self.cursor.x2 = x

        freq = self.detector.get_frequency()
        if freq is None:
            return

        self.handle_voice_input(song_time, x, freq)

    def handle_voice_input(self, songtime, x, p_freq):
        """Handles the voice input and updates the game state accordingly. 

        If the player's pitch is within a certain range of the target note's frequency,
        it creates a visual point and updates the score.
        """

        current_note = self.get_current_note(songtime)

        if current_note and p_freq is not None:
            diff = cents_diff(p_freq, current_note["freq"])
            print(
                "time:", round(songtime, 2),
                "target:", round(current_note["freq"], 2),
                "played:", round(p_freq, 2),
                "cents:", round(diff, 1)
            )

            if abs(diff) <= 50:  # Snapping to target note if close enough
                self.create_voice_point(x, current_note["freq"])
                self.score += self.calculate_points(abs(diff))
                self.pitch_info.text = "Perfect!"
                self.score_label.text = f"Score: {self.score}"

            elif abs(diff) <= 150:
                self.create_voice_point(x, p_freq, 90)
                self.score += self.calculate_points(abs(diff))
                self.pitch_info.text = "Good"
                self.score_label.text = f"Score: {self.score}"
            else:
                self.create_voice_point(x, p_freq, 60)
                info = self.get_pitch_info(diff)
                self.pitch_info.text = info


class PitchDetector:
    def __init__(self, rate, chunk_size):
        self.rate = rate
        self.chunk_size = chunk_size

        self.latest_freq = None
        self.freq_history = deque(maxlen=3)

   # audio callback to safe data
    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)

        data = indata[:, 0]  # mono
        freq = self.detect_live_frequency(data, RATE)

        if freq is not None:
            self.freq_history.append(freq)
            if len(self.freq_history) >= 2:
                self.latest_freq = float(np.median(self.freq_history))
        else:
            self.latest_freq = None

    def fundamental_hps(self, magnitude, freqs, max_harmonics=5, fmin=50, fmax=2000):
        """Detects the fundamental frequency using the Harmonic Product Spectrum (HPS) method.

        Made with help of ChatGPT - Prompt: "Given a set of frequencies from an FFT in python,
        how can I get the fundamental frequency, even if harmonics are louder ?"
        """
        hps = magnitude.copy()
        for h in range(2, max_harmonics + 1):
            downsampled = magnitude[::h]
            hps[:len(downsampled)] *= downsampled
        # Suchbereich einschränken
        mask = (freqs >= fmin) & (freqs <= fmax)
        hps_search = hps[mask]
        freqs_search = freqs[mask]
        if len(hps_search) == 0:
            return None
        peak_idx = np.argmax(hps_search)
        return freqs_search[peak_idx]

    def detect_live_frequency(self, data, rate):
        """Detects the dominant frequency in the given audio data and prints it.

        Made with the help of ChatGPT - Prompt "get freqeuncy from live audio in python using np.rfft"
        """
        if np.max(np.abs(data)) < 0.05:
            return None

        # Perform FFT to get frequency spectrum
        win = np.hamming(len(data))
        fft_result = np.fft.rfft(data * win)
        magnitudes = np.abs(fft_result)
        freqs = np.fft.rfftfreq(len(data), 1/rate)

    # Spektrum behalten, damit Obertöne noch da sind
        spec_mask = freqs <= 2000
        freqs_hps = freqs[spec_mask]
        mag_hps = magnitudes[spec_mask]

        # Grundfrequenz nur in sinnvollem Bereich suchen
        peak_freq = self.fundamental_hps(
            mag_hps,
            freqs_hps,
            max_harmonics=4,
            fmin=80,
            fmax=800
        )

        return peak_freq

    def get_frequency(self):
        return self.latest_freq


def midi_note_to_freq(note):
    return 440.0 * (2 ** ((note - 69) / 12))


def cents_diff(freq_1, freq_2):
    """Calculate the difference in cents between two frequencies.

    More accurate way for calucating pitch difference in music context.
    """
    return 1200 * np.log2(freq_1 / freq_2)


def read_midi(midi_file):
    """Reads a MIDI file and extracts note information.

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


def run_game():
    win = pyglet.window.Window(1280, 800)
    pitch_detector = PitchDetector(RATE, CHUNK_SIZE)
    input_device = get_input_decive()
    song_name, song_file = get_karaoke_song()
    game = Game(song_file, pitch_detector, win)
    bg = pyglet.image.load(f"{BACKGROUND_PATH}")

    @win.event
    def on_key_press(symbol, modifiers):
        if symbol == key.SPACE:
            game.start()

    @win.event
    def on_draw():
        win.clear()
        bg.blit(0, 0, width=win.width, height=win.height)
        game.draw()

    # open audio input stream
    stream = sd.InputStream(
        device=input_device,
        channels=CHANNELS,
        samplerate=RATE,
        blocksize=CHUNK_SIZE,
        callback=pitch_detector.audio_callback,
        latency='low'
    )

    stream.start()
    pyglet.clock.schedule_interval(game.update, 1/30)
    pyglet.app.run()
    stream.stop()
    stream.close()


if __name__ == "__main__":
    run_game()
