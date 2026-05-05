import argparse
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Sequence, Tuple

import cv2
import mediapipe as mp

try:
    from pynput.keyboard import Controller, Key
except Exception:  # pragma: no cover - environment-specific import failure.
    Controller = None
    Key = None


class Gesture(str, Enum):
    ACCELERATE = "ACCELERATING"
    BRAKE = "BRAKING"
    NEUTRAL = "NEUTRAL"


@dataclass
class FingerState:
    thumb_open: bool
    index_open: bool
    middle_open: bool
    ring_open: bool
    pinky_open: bool

    @property
    def open_count(self) -> int:
        return sum(
            [
                self.thumb_open,
                self.index_open,
                self.middle_open,
                self.ring_open,
                self.pinky_open,
            ]
        )

    @property
    def is_open_hand(self) -> bool:
        return self.open_count == 5

    @property
    def is_fist(self) -> bool:
        return self.open_count == 0


class KeyDriver:
    def __init__(self) -> None:
        if Controller is None or Key is None:
            raise RuntimeError(
                "Keyboard control is unavailable. Ensure pynput is installed and the "
                "OS allows keyboard event injection."
            )
        self.keyboard = Controller()
        self.pressed_right = False
        self.pressed_left = False

    def set_state(self, gesture: Gesture) -> None:
        if gesture == Gesture.ACCELERATE:
            self._press_right()
            self._release_left()
        elif gesture == Gesture.BRAKE:
            self._press_left()
            self._release_right()
        else:
            self._release_left()
            self._release_right()

    def release_all(self) -> None:
        self._release_left()
        self._release_right()

    def _press_right(self) -> None:
        if not self.pressed_right:
            self.keyboard.press(Key.right)
            self.pressed_right = True

    def _release_right(self) -> None:
        if self.pressed_right:
            self.keyboard.release(Key.right)
            self.pressed_right = False

    def _press_left(self) -> None:
        if not self.pressed_left:
            self.keyboard.press(Key.left)
            self.pressed_left = True

    def _release_left(self) -> None:
        if self.pressed_left:
            self.keyboard.release(Key.left)
            self.pressed_left = False


class GestureController:
    def __init__(
        self,
        confidence: float = 0.7,
        smooth_frames: int = 4,
        use_right_hand_only: bool = True,
    ) -> None:
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=confidence,
            min_tracking_confidence=confidence,
        )
        self.key_driver = KeyDriver()
        self.smooth_frames = max(1, smooth_frames)
        self.last_raw: Gesture = Gesture.NEUTRAL
        self.last_stable: Gesture = Gesture.NEUTRAL
        self.raw_streak = 0
        self.use_right_hand_only = use_right_hand_only
        self.enabled = True
        self.last_toggle = 0.0

    def run(self, camera_index: int = 0) -> None:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise RuntimeError("Could not open webcam. Check camera permissions and index.")

        cv2.namedWindow("Gesture Controller", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Gesture Controller", 460, 700)
        cv2.moveWindow("Gesture Controller", 10, 60)

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                frame = cv2.flip(frame, 1)
                raw_gesture, handedness_label, annotated = self._process_frame(frame)
                stable_gesture = self._smooth(raw_gesture)

                if self.enabled:
                    self.key_driver.set_state(stable_gesture)
                else:
                    self.key_driver.release_all()

                panel = self._build_panel(annotated, stable_gesture, handedness_label)
                cv2.imshow("Gesture Controller", panel)

                pressed = cv2.waitKey(1) & 0xFF
                if pressed in (ord("q"), 27):
                    break
                if pressed == ord("t"):
                    now = time.time()
                    if now - self.last_toggle > 0.25:
                        self.enabled = not self.enabled
                        self.last_toggle = now
                        if not self.enabled:
                            self.key_driver.release_all()
        finally:
            self.key_driver.release_all()
            cap.release()
            cv2.destroyAllWindows()

    def _process_frame(self, frame) -> Tuple[Gesture, str, Any]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)
        handedness = "None"
        gesture = Gesture.NEUTRAL

        if result.multi_hand_landmarks and result.multi_handedness:
            landmarks = result.multi_hand_landmarks[0]
            handedness = result.multi_handedness[0].classification[0].label

            if not self.use_right_hand_only or handedness == "Right":
                fingers = self._finger_state(landmarks, handedness)
                gesture = self._classify(fingers)
                self.mp_draw.draw_landmarks(
                    frame, landmarks, self.mp_hands.HAND_CONNECTIONS
                )
            else:
                gesture = Gesture.NEUTRAL

        return gesture, handedness, frame

    def _finger_state(self, landmarks, handedness: str) -> FingerState:
        lm = landmarks.landmark
        tips = self.mp_hands.HandLandmark

        index_open = lm[tips.INDEX_FINGER_TIP].y < lm[tips.INDEX_FINGER_PIP].y
        middle_open = lm[tips.MIDDLE_FINGER_TIP].y < lm[tips.MIDDLE_FINGER_PIP].y
        ring_open = lm[tips.RING_FINGER_TIP].y < lm[tips.RING_FINGER_PIP].y
        pinky_open = lm[tips.PINKY_TIP].y < lm[tips.PINKY_PIP].y

        # Thumb uses x-axis relation and depends on left/right handedness.
        if handedness == "Right":
            thumb_open = lm[tips.THUMB_TIP].x < lm[tips.THUMB_IP].x
        else:
            thumb_open = lm[tips.THUMB_TIP].x > lm[tips.THUMB_IP].x

        return FingerState(
            thumb_open=thumb_open,
            index_open=index_open,
            middle_open=middle_open,
            ring_open=ring_open,
            pinky_open=pinky_open,
        )

    def _classify(self, fingers: FingerState) -> Gesture:
        if fingers.is_open_hand:
            return Gesture.ACCELERATE
        if fingers.is_fist:
            return Gesture.BRAKE
        return Gesture.NEUTRAL

    def _smooth(self, raw: Gesture) -> Gesture:
        if raw == self.last_raw:
            self.raw_streak += 1
        else:
            self.last_raw = raw
            self.raw_streak = 1

        if self.raw_streak >= self.smooth_frames:
            self.last_stable = raw
        return self.last_stable

    def _build_panel(self, frame, stable_gesture: Gesture, handedness: str):
        h, w = frame.shape[:2]
        panel_height = 150
        panel = cv2.copyMakeBorder(
            frame, 0, panel_height, 0, 0, cv2.BORDER_CONSTANT, value=(20, 20, 20)
        )

        enabled_text = "ON" if self.enabled else "OFF"
        color = (0, 200, 0) if stable_gesture == Gesture.ACCELERATE else (0, 165, 255)
        if stable_gesture == Gesture.NEUTRAL:
            color = (180, 180, 180)

        cv2.putText(
            panel,
            f"Mode: {enabled_text} (press 't' to toggle)",
            (14, h + 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (230, 230, 230),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            panel,
            f"Hand: {handedness}",
            (14, h + 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (230, 230, 230),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            panel,
            f"State: {stable_gesture.value}",
            (14, h + 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            color,
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            panel,
            "q/ESC to quit",
            (w - 160, h + 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),
            2,
            cv2.LINE_AA,
        )
        return panel


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-hand gesture controller for Hill Climb Racing Lite"
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Webcam index passed to OpenCV VideoCapture",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.7,
        help="MediaPipe detection/tracking confidence",
    )
    parser.add_argument(
        "--smooth-frames",
        type=int,
        default=4,
        help="Frames required before switching gesture state",
    )
    parser.add_argument(
        "--allow-left-hand",
        action="store_true",
        help="Disable right-hand-only filter",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    controller = GestureController(
        confidence=args.confidence,
        smooth_frames=args.smooth_frames,
        use_right_hand_only=not args.allow_left_hand,
    )
    controller.run(camera_index=args.camera_index)


if __name__ == "__main__":
    main()
