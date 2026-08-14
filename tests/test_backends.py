"""Tests for the backend command wrapper (timeout, exit codes)."""

from __future__ import annotations

import unittest

from conveyr.backends import BackendError, run


class RunTest(unittest.TestCase):
    def test_success(self):
        proc = run(["true"])
        self.assertEqual(proc.returncode, 0)

    def test_failure_raises(self):
        with self.assertRaises(BackendError):
            run(["false"])

    def test_ok_codes_accepted(self):
        proc = run(["sh", "-c", "exit 3"], ok_codes=(0, 3))
        self.assertEqual(proc.returncode, 3)

    def test_missing_binary_raises(self):
        with self.assertRaises(BackendError):
            run(["conveyr-this-binary-does-not-exist"])

    def test_timeout_raises(self):
        with self.assertRaises(BackendError) as ctx:
            run(["sleep", "5"], timeout=0.3)
        self.assertIn("timed out", str(ctx.exception).lower())

    def test_no_timeout_when_fast(self):
        run(["sleep", "0"], timeout=2)


if __name__ == "__main__":
    unittest.main()