# Gesture Controller for Hill Climb Racing Lite

Real-time one-hand gesture controller for the browser game [Hill Climb Racing Lite](https://poki.com/en/g/hill-climb-racing-lite).

## Demo

D:\gesture based game\docs\gesture_demo.mp4

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

If you already had the environment from an older install, run `pip install -r requirements.txt --upgrade` once to align package versions.

## Run (Recommended)

```bash
python run.py
```

Default launcher behavior:

- Open the game page directly in browser
- Run a quick `--self-check`
- Start the gesture controller with webcam preview enabled
- Keep keyboard control active while you play in the game tab

## Direct Controller Only

```bash
python main.py --camera-index 0 --confidence 0.7 --smooth-frames 4
```

Use this if you want only the controller process without launcher automation.

## Useful Launcher Flags

```bash
python run.py --preview
python run.py --ui-mode web
python run.py --runner-port 8090 --ports 8090
python run.py --open both
python run.py --kill-only
python run.py --allow-left-hand
```

## Runtime Notes

- Default mode is `legacy`, optimized for "open game + run webcam controller concurrently".
- Web mode (`--ui-mode web`) is optional and starts a local runner server.
- Keep the game tab/window focused for keyboard input capture.
- Press `t` in preview window to toggle control ON/OFF.
- Press `q` or `Esc` in preview window to quit.
- Press `Ctrl+C` in terminal to stop launcher/controller.

## Validation

Automated checks:

```bash
.venv\Scripts\python.exe -m py_compile main.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe main.py --self-check --camera-index 0
```

Manual checks (required for final gameplay validation):

1. Start the app and verify key behavior in Notepad:
   - Open hand types/holds Right Arrow navigation behavior.
   - Fist types/holds Left Arrow navigation behavior.
   - Transitional gestures release both keys.
2. Focus Hill Climb Racing Lite and verify the same behavior in-game.
3. Tune `--confidence` and `--smooth-frames` for your lighting and camera.

## Recommended Play Layout

1. Start `python run.py`.
2. Wait for webcam preview window to appear.
3. Place preview where you can see it while playing.
4. Keep the game tab/window focused.
5. Use open-hand and fist gestures to drive and brake.
