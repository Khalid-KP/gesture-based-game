import unittest

from main import FingerState, Gesture, GestureController, parse_args


class FingerStateTests(unittest.TestCase):
    def test_open_hand_and_fist_detection(self) -> None:
        open_hand = FingerState(True, True, True, True, True)
        fist = FingerState(False, False, False, False, False)

        self.assertTrue(open_hand.is_open_hand)
        self.assertFalse(open_hand.is_fist)
        self.assertEqual(open_hand.open_count, 5)

        self.assertTrue(fist.is_fist)
        self.assertFalse(fist.is_open_hand)
        self.assertEqual(fist.open_count, 0)


class GestureLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = GestureController.__new__(GestureController)
        self.controller.smooth_frames = 3
        self.controller.last_raw = Gesture.NEUTRAL
        self.controller.last_stable = Gesture.NEUTRAL
        self.controller.raw_streak = 0

    def test_classify_open_hand_to_accelerate(self) -> None:
        gesture = self.controller._classify(FingerState(True, True, True, True, True))
        self.assertEqual(gesture, Gesture.ACCELERATE)

    def test_classify_fist_to_brake(self) -> None:
        gesture = self.controller._classify(FingerState(False, False, False, False, False))
        self.assertEqual(gesture, Gesture.BRAKE)

    def test_smoothing_requires_threshold_frames(self) -> None:
        self.assertEqual(self.controller._smooth(Gesture.ACCELERATE), Gesture.NEUTRAL)
        self.assertEqual(self.controller._smooth(Gesture.ACCELERATE), Gesture.NEUTRAL)
        self.assertEqual(self.controller._smooth(Gesture.ACCELERATE), Gesture.ACCELERATE)


class CliTests(unittest.TestCase):
    def test_allow_left_hand_flag(self) -> None:
        args = parse_args(["--allow-left-hand", "--smooth-frames", "6"])
        self.assertTrue(args.allow_left_hand)
        self.assertEqual(args.smooth_frames, 6)

    def test_self_check_flag(self) -> None:
        args = parse_args(["--self-check"])
        self.assertTrue(args.self_check)

    def test_no_window_flag(self) -> None:
        args = parse_args(["--no-window"])
        self.assertTrue(args.no_window)


if __name__ == "__main__":
    unittest.main()
