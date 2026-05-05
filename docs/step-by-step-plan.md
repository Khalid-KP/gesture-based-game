# Step-by-Step Plan

## Phase 1 - Foundation

1. Create project skeleton (`main.py`, `requirements.txt`, `README.md`, `docs/`).
2. Install core libraries:
   - `mediapipe`
   - `opencv-python`
   - `pynput`
3. Confirm webcam opens and can render a live frame.

## Phase 2 - Hand Tracking

1. Initialize MediaPipe Hands (`max_num_hands=1`).
2. Track one hand and draw landmarks.
3. Restrict to right hand for one-hand MVP.

## Phase 3 - Gesture Classification

1. Infer finger open/closed states from landmark geometry.
2. Classify:
   - Open hand -> ACCELERATING
   - Fist -> BRAKING
   - Anything else -> NEUTRAL
3. Add frame smoothing to reduce flicker and unstable switching.

## Phase 4 - Keyboard Output

1. Use `pynput` key down/up events.
2. Map gestures:
   - ACCELERATING -> hold Right Arrow
   - BRAKING -> hold Left Arrow
   - NEUTRAL -> release both
3. Add safe toggle key (`t`) to enable/disable output quickly.

## Phase 5 - UX Overlay

1. Show webcam view in a movable/resizeable left panel.
2. Add status box under camera:
   - Mode ON/OFF
   - Detected hand
   - Current game action
3. Add quit shortcut (`q`/`Esc`).

## Phase 6 - Validation

1. Test gestures in Notepad first (key behavior sanity check).
2. Test with Hill Climb Racing Lite in focused browser window.
3. Tune confidence and smoothing if needed.

## Phase 7 - Push-Ready Checks

1. Verify script runs without syntax errors.
2. Ensure docs are clear and complete.
3. Keep commit clean and scoped to MVP.
