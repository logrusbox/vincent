import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Event, Timer
import time
import unittest

from mission_control.codex_runner import CodexRunner, CodexFailure
from mission_control.process_control import run_bounded, ExecutionInterrupted


class ProcessControlTests(unittest.TestCase):
    def run_process(self, code, **kwargs):
        return run_bounded([sys.executable, '-c', code], cwd=Path('.'), input='', **kwargs)

    def test_hung_process_is_bounded_and_partial_output_preserved(self):
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.run_process('import time; print("checkpoint",flush=True); time.sleep(60)', timeout=0.2, grace=0.1)
        self.assertIn('checkpoint', caught.exception.output)
        self.assertLess(time.monotonic() - started, 3)

    def test_cancellation_stops_running_provider(self):
        cancelled = Event()
        timer = Timer(0.2, cancelled.set)
        timer.start()
        try:
            with self.assertRaises(ExecutionInterrupted):
                self.run_process('import time; time.sleep(60)', timeout=30, cancel=cancelled, grace=0.1)
        finally:
            timer.join()

    def test_process_group_descendant_cannot_keep_pipes_open(self):
        code = ('import subprocess,sys,time; '
                'subprocess.Popen([sys.executable,"-c","import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"]); '
                'time.sleep(60)')
        start = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_process(code, timeout=0.3, grace=0.1)
        self.assertLess(time.monotonic() - start, 3)

    def test_missing_bound_never_starts_provider(self):
        def forbidden(*args, **kwargs):
            raise AssertionError('must not launch')
        result = CodexRunner(process_runner=forbidden).execute(Path('.'), 'task')
        self.assertFalse(result.succeeded)
        self.assertIn('bound required', result.stderr)

    def test_adapter_distinguishes_timeout_and_interruption(self):
        for exception, expected in ((subprocess.TimeoutExpired('test', 1), CodexFailure.TIMEOUT),
                                    (ExecutionInterrupted(), CodexFailure.INTERRUPTED)):
            def failed(*args, **kwargs):
                raise exception
            result = CodexRunner(process_runner=failed, timeout_seconds=1).execute(Path('.'), 'task')
            self.assertEqual(result.failure, expected)

    def test_completed_output_and_status_are_preserved(self):
        result = self.run_process('print("ok")', timeout=5)
        self.assertEqual((result.returncode, result.stdout), (0, 'ok\n'))


if __name__ == '__main__':
    unittest.main()
