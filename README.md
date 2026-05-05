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

If you already had the environment from an older install, run `pip install -r requirements.txt --upgrade` once to align package versions.

## Run

```bash
python run.py
```

Direct controller mode (without launcher):

```bash
python main.py
```

`python run.py` will:

- Open a local web runner at `http://localhost:8080` with the game embedded
- Run a quick `--self-check`
- Start the gesture controller in `--no-window` mode for better keyboard sync
- Stream live webcam preview/state into the same web page (`/api/frame`, `/api/state`)

Use CLI flags on `run.py` to tune camera index, confidence, smoothing, or allow-left-hand behavior.

Optional flags:

```bash
python run.py --ui-mode legacy --preview
python run.py --open both
python run.py --kill-only
python main.py --camera-index 0 --confidence 0.7 --smooth-frames 4
python main.py --allow-left-hand
python main.py --self-check
python main.py --no-window
```

## Runtime Notes

- Launcher default (`--ui-mode web`) keeps one-page mode and ignores `--preview`.
- Use `python run.py --ui-mode legacy --preview` only for old OpenCV-window workflow.
- Keep the game tab/window focused when control is ON.
- In legacy preview mode, press `t` to toggle input ON/OFF.
- In legacy preview mode, press `q` or `Esc` to quit.
- In no-window mode, stop from terminal with `Ctrl+C`.

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
2. Open `http://localhost:8080` if it did not auto-open.
3. Wait for webcam preview to appear in the left panel.
4. Click `Enable Control`, then `Focus Game`.
5. Keep this tab focused and play with hand gestures.
