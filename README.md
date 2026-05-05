# Gesture Controller for Hill Climb Racing Lite

Real-time one-hand gesture controller for the browser game [Hill Climb Racing Lite](https://poki.com/en/g/hill-climb-racing-lite).

## Controls

- Open hand -> hold Right Arrow (accelerate)
- Fist -> hold Left Arrow (brake)
- Unknown/transition -> release both keys (safety)

## Requirements

- Python 3.10+
- Webcam
- Browser with game focused (keyboard input must go to the game tab/window)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Optional flags:

```bash
python main.py --camera-index 0 --confidence 0.7 --smooth-frames 4
python main.py --allow-left-hand
```

## Runtime Notes

- Keep the webcam window visible on the left side of your screen.
- Keep the game tab/window focused when control is ON.
- Press `t` to toggle input ON/OFF.
- Press `q` or `Esc` to quit.

## Recommended Play Layout

1. Open Hill Climb Racing Lite in browser.
2. Place game window on the right side.
3. Start `python main.py`.
4. Keep the webcam panel on the left side.
5. Focus the game window and play with hand gestures.
