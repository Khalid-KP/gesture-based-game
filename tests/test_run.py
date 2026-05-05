import sys
import unittest

import run


class RunCliTests(unittest.TestCase):
    def test_parse_ports_filters_invalid_values(self) -> None:
        ports = run.parse_ports("8080, -1, abc, 65536, 5000 8080")
        self.assertEqual(ports, [5000, 8080])

    def test_default_ui_mode_is_web(self) -> None:
        old_argv = sys.argv
        try:
            sys.argv = ["run.py"]
            args = run.parse_args()
        finally:
            sys.argv = old_argv
        self.assertEqual(args.ui_mode, "web")


if __name__ == "__main__":
    unittest.main()
