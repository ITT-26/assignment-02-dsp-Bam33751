[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/B3oR_XLF)

# Karaoke Game & Whistle Input

This project contains two separate applications:

- Karaoke Game  
- Whistle Input (Chirp Control)

---

## Karaoke Game

### Setup

Install all required dependencies using the provided requirements file:

```
pip install -r requirements.txt
```

---

### Important Note on File Paths

Before running the program, make sure that the file paths are correct.

In `karaoke.py`, there are constants at the top of the file that define paths for:

- MIDI files  
- WAV files  
- Background image  

Depending on your current working directory, you may need to adjust these paths manually.

---

### How to Run

python karaoke.py

---

### Controls and Flow

1. Select your audio input device in the terminal  
2. Select a song:
   - Berge  
   - Freude  
3. A game window opens  
4. Press SPACE to start  
5. A countdown appears: 3 → 2 → 1 → GO  
6. Start singing  

---

### Gameplay

For the best experience, please use headphones to avoid microphone–speaker interference. Alternatively, you can use an external input device such as a smartphone, but make sure it is not placed too close to the speakers.

During the game, target notes are displayed as visual hints.

Your sung frequency is detected in real time and mapped to these target notes.

A moving cursor shows your current position in the song.

You receive a score based on how accurately your singing matches the notes.


<p align="center">

  <img src="docs/karaoke.png" alt="Karaoke Game Screenshot" width="700">

</p>
---

## Whistle Input

### Setup

Install the required dependencies if you haven't done it before:

```
pip install -r requirements.txt
```

---

### How to Run

python whistle-input.py

---

### Demo Interface

When the program starts, a small pyglet window opens.

It displays three rectangles.

The currently selected rectangle is highlighted with a blue border

---

### Whistle Controls

The selection can be controlled using whistled chirps:

- Up-chirp → move selection up  
- Down-chirp → move selection down  

---

### What is a Chirp?

A chirp is a continuous change in frequency:

- Up-chirp: low → high  
- Down-chirp: high → low  

---

### Important Constraints

The whistle must be continuous.

You must first whistle one tone and then directly transition to another tone.

Detection may fail if there is a pause between the tones.

Only a short pause of about 0.3 seconds is tolerated.

The frequency difference must be at least about 300 Hz.

For best results:

- whistle clearly  
- whistle loudly enough  
- keep the pitch change continuous  

---

### Global Keyboard Control

The program can also control other applications.

When a chirp is detected:

- Up-chirp triggers the Arrow Up key  
- Down-chirp triggers the Arrow Down key  

This allows navigation in other applications.

---

### macOS Note
These applications where created on mac os, you may need to adjust the window size of the pyglet apllications for better expierence. 

---

## Summary

The Karaoke Game performs real-time pitch tracking and scoring based on how well the user matches target notes.

The Whistle Input system detects upward and downward frequency chirps and maps them to navigation actions in a GUI and external applications.