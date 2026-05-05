# Step-by-Step Plan

## Phase 1 - Foundation

Status: DONE

1. Create project skeleton (`main.py`, `requirements.txt`, `README.md`, `docs/`).
2. Install core libraries:
   - `mediapipe`
   - `opencv-python`
   - `pynput`
3. Confirm webcam opens and can render a live frame.

Completion notes:

- Virtual environment created at `.venv/`
- Dependencies installed successfully via `requirements.txt`
- Webcam smoke test result: `CAM_OPEN True`

## Phase 2 - Hand Tracking

Status: DONE

1. Initialize MediaPipe Hands (`max_num_hands=1`).
2. Track one hand and draw landmarks.
3. Restrict to right hand for one-hand MVP.

Completion notes:

- Configured `max_num_hands=1` in `main.py`
- Rendering hand landmarks with MediaPipe drawing utilities
- Right-hand-only filtering enabled by default (`--allow-left-hand` to override)

## Phase 3 - Gesture Classification

Status: DONE

1. Infer finger open/closed states from landmark geometry.
2. Classify:
   - Open hand -> ACCELERATING
   - Fist -> BRAKING
   - Anything else -> NEUTRAL
3. Add frame smoothing to reduce flicker and unstable switching.

Completion notes:

- Finger state inference uses MediaPipe landmark geometry for all five fingers
- Gesture mapping now follows exact phase rules: open hand -> `ACCELERATING`, fist -> `BRAKING`, otherwise `NEUTRAL`
- Temporal smoothing is applied via frame streak threshold (`--smooth-frames`)

## Phase 4 - Keyboard Output

Status: DONE

1. Use `pynput` key down/up events.
2. Map gestures:
   - ACCELERATING -> hold Right Arrow
   - BRAKING -> hold Left Arrow
   - NEUTRAL -> release both
3. Add safe toggle key (`t`) to enable/disable output quickly.

Completion notes:

- `KeyDriver` handles key-down/key-up events with press-state guards.
- Gesture mapping is wired as specified: accelerate->Right, brake->Left, neutral->release both.
- Safe runtime toggle is implemented on `t` with debounce and immediate key release when OFF.

## Phase 5 - UX Overlay

Status: DONE

1. Show webcam view in a movable/resizeable left panel.
2. Add status box under camera:
   - Mode ON/OFF
   - Detected hand
   - Current game action
3. Add quit shortcut (`q`/`Esc`).

Completion notes:

- OpenCV panel uses normal window mode with explicit left-side placement and resizable behavior.
- Overlay renders mode state, detected hand label, and current stable action.
- Quit flow supports both `q` and `Esc` with cleanup that releases keys and closes windows.

## Phase 6 - Validation

1. Test gestures in Notepad first (key behavior sanity check).
2. Test with Hill Climb Racing Lite in focused browser window.
3. Tune confidence and smoothing if needed.

Completion notes:

- Added automated validation commands:
  - `.venv\Scripts\python.exe -m py_compile main.py`
  - `.venv\Scripts\python.exe -m unittest discover -s tests -v`
  - `.venv\Scripts\python.exe main.py --self-check --camera-index 0`
- Added unit tests for finger-state logic, gesture classification, smoothing threshold, and CLI parsing.
- Added runtime `--self-check` mode to validate keyboard driver, camera access, and MediaPipe initialization.
- Manual gameplay validation in Notepad + browser still required on target machine.

## Phase 7 - Push-Ready Checks

1. Verify script runs without syntax errors.
2. Ensure docs are clear and complete.
3. Keep commit clean and scoped to MVP.

Completion notes:

- Syntax verification is automated with `py_compile`.
- Docs now include an explicit validation section (automated + manual checks).
- Commit scope remains limited to reliability, test coverage, and validation docs.

---

## Checklist (Ticked So Far)

- [x] Phase 1 - Foundation
  - [x] Project skeleton created
  - [x] Core libraries installed (`mediapipe`, `opencv-python`, `pynput`)
  - [x] Webcam smoke test passed

- [x] Phase 2 - Hand Tracking
  - [x] MediaPipe Hands initialized with one-hand tracking
  - [x] Hand landmarks drawn on webcam frame
  - [x] Right-hand restriction applied for MVP

- [x] Phase 3 - Gesture Classification
  - [x] Finger open/closed inference from landmarks
  - [x] Gesture mapping to ACCELERATING/BRAKING/NEUTRAL
  - [x] Frame smoothing added

- [x] Phase 4 - Keyboard Output
  - [x] `pynput` key down/up handling
  - [x] Gesture-to-key mapping implemented
  - [x] Safe toggle key (`t`) implemented

- [x] Phase 5 - UX Overlay
  - [x] Webcam panel window and placement controls
  - [x] Status box (mode, hand, state)
  - [x] Quit shortcuts (`q` / `Esc`)

- [~] Phase 6 - Validation
  - [ ] Notepad key-behavior sanity test (manual)
  - [ ] Hill Climb Racing Lite focused-window test (manual)
  - [ ] Confidence/smoothing tuning pass (manual)
  - [x] Automated validation checks added and passing

- [x] Phase 7 - Push-Ready Checks
  - [x] Final syntax/run verification pass
  - [x] Final docs polish pass
  - [x] Commit hygiene review
