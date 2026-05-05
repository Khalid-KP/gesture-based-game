# Technical Overview: Gesture-Based Game Controller

## 1) Project Purpose

This project turns one-hand gestures captured from a webcam into keyboard controls for **Hill Climb Racing Lite**:

- Open hand -> hold `Right Arrow` (accelerate)
- Fist -> hold `Left Arrow` (brake)
- Transitional/unknown gesture -> release both keys (safety neutral)

The runtime is optimized for direct gameplay control (game tab + webcam controller concurrently), with optional web runner mode.

## 2) Core Stack

- **Python 3.10+**
- **MediaPipe Hands** (`mediapipe==0.10.14`) for hand landmark estimation
- **OpenCV** (`opencv-python`) for webcam capture, frame operations, optional preview rendering
- **pynput** for keyboard event injection (`press`/`release` arrow keys)
- Built-in Python HTTP server primitives for local API endpoints/UI integration

## 3) High-Level Architecture

### Execution Components

1. **Launcher** (`run.py`)
   - Cleans previous sessions/processes
   - Runs preflight self-check
   - Starts gesture controller process
   - Optionally starts local web server (`http://localhost:8090`) in web mode

2. **Gesture Engine** (`main.py`)
   - Captures camera frames
   - Runs MediaPipe hand inference
   - Classifies gestures using landmark geometry
   - Applies temporal smoothing
   - Sends keyboard actions
   - Publishes runtime state + frame snapshots for the web UI

3. **Browser UI** (`web/index.html`, optional web mode)
   - Displays game iframe
   - Displays webcam preview (from backend frame stream)
   - Polls live state endpoint
   - Toggles controller ON/OFF
   - Provides fallback action when game embedding is blocked

## 4) Gesture Algorithm

### 4.1 Landmark-Based Finger State Detection

For each frame, MediaPipe returns 21 hand landmarks. Finger open/closed states are inferred using geometric rules:

- **Index/Middle/Ring/Pinky**  
  Finger is considered open when:
  - `TIP.y < PIP.y`
  (in image coordinates, smaller y is higher on frame)

- **Thumb**  
  Uses x-axis relation and depends on handedness:
  - Right hand: `THUMB_TIP.x < THUMB_IP.x` -> open
  - Left hand: `THUMB_TIP.x > THUMB_IP.x` -> open

This produces a `FingerState` object:

- `thumb_open`, `index_open`, `middle_open`, `ring_open`, `pinky_open`
- `open_count` in range `[0..5]`

### 4.2 Gesture Classification Rules

Rule-based classifier maps finger states to game intent:

- `open_count >= 4` -> `ACCELERATING`
- `open_count <= 1` -> `BRAKING`
- otherwise -> `NEUTRAL`

This deterministic mapping avoids ambiguous mixed gestures triggering accidental key presses.

## 5) Temporal Smoothing Technique

To reduce flicker/noise from single-frame misclassification, the controller uses a **streak-threshold stabilizer**:

- Track current `last_raw` gesture and `raw_streak` count
- Increment streak only when consecutive raw outputs match
- Promote raw -> stable only after `raw_streak >= smooth_frames`
- Drive key output from `last_stable`, not from raw frame-by-frame outputs

Default:

- `smooth_frames = 4`

Effect:

- Improves stability
- Adds small switching latency (trade-off controlled by parameter)

## 6) Keyboard Control Technique

`KeyDriver` maintains explicit pressed-state flags:

- `pressed_right`
- `pressed_left`

Press/release operations are guarded to avoid duplicate key events:

- Accelerate: press right, release left
- Brake: press left, release right
- Neutral: release both

This acts as a small finite-state controller and prevents stuck-key behavior during transitions.

## 7) Safety and Control Semantics

Safety mechanisms include:

- **Neutral fallback** on mid-state gestures (`open_count` in `[2, 3]`)
- **Right-hand-only filter** by default (reduces false triggers)
- UI control toggle (`enabled`) that forces key release when OFF
- Final cleanup on shutdown always releases keys

## 8) Runtime Data Bridge (Web Mode)

In web mode, launcher and controller communicate via local runtime files under `.runtime/`:

- `gesture-state.json` (published state)
- `gesture-control.json` (UI control requests)
- `gesture-frame.jpg` (latest preview frame)

Local API endpoints:

- `GET /api/state` -> current mode/gesture/handedness
- `POST /api/control` -> set `enabled: true|false`
- `GET /api/frame` -> latest JPEG preview

UI polling intervals (current defaults in page script):

- State polling: ~200 ms
- Frame refresh: ~150 ms

## 9) Tunable Parameters

### Main Controller (`main.py`)

- `--camera-index` (int, default `0`)  
  Selects webcam device index for OpenCV.

- `--confidence` (float, default `0.7`)  
  Used for both MediaPipe detection and tracking confidence thresholds.

- `--smooth-frames` (int, default `4`)  
  Consecutive matching frames required to switch stable state.

- `--allow-left-hand` (flag, default `False`)  
  Disables right-hand-only filtering when enabled.

- `--self-check` (flag)  
  Runs keyboard/camera/MediaPipe validation and exits.

- `--no-window` (flag)  
  Runs controller without OpenCV preview window.

- `--status-file`, `--control-file`, `--frame-file`  
  Optional integration paths for state/control/frame bridge in web mode.

### Launcher (`run.py`)

- `--ports` (default `"8090"`)  
  Comma-separated ports to free before restart.

- `--runner-host` (default `"0.0.0.0"`)  
  Host/IP used to bind the optional local web runner.

- `--runner-port` (default `8090`)  
  Port used by optional local web runner mode.

- `--kill-only`  
  Cleanup without starting runner/controller.

- `--open {runner,game,both}` (default `game`)  
  Controls which page(s) to open in browser.

- `--ui-mode {web,legacy}` (default `legacy`)  
  `legacy`: direct game + OpenCV preview flow  
  `web`: optional single-page runner flow

- `--preview/--no-preview` (default `True`)  
  Controls OpenCV preview visibility (legacy mode).

## 10) Validation Strategy

1. **Static/Syntax**
   - `python -m py_compile main.py run.py`

2. **Unit Tests**
   - Finger-state and gesture classification tests
   - Smoothing threshold tests
   - CLI argument parsing tests

3. **Runtime Self-Check**
   - Keyboard driver initialization
   - Camera open/read
   - MediaPipe Hands initialization

4. **Manual E2E**
   - Launch `python run.py`
   - Keep game tab focused
   - Verify open hand / fist / neutral behavior live

## 11) Known Trade-offs

- Rule-based gesture logic is lightweight and deterministic, but less expressive than ML classifiers trained on custom gesture datasets.
- Streak smoothing improves stability but introduces switching delay proportional to `smooth_frames`.
- Keyboard injection behavior can vary across OS permissions and browser focus rules.
