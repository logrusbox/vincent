"""Linux provider process bounds with preserved output and group termination."""
from __future__ import annotations

import os
import signal
import subprocess
from threading import Event
import time


class ExecutionInterrupted(RuntimeError):
    def __init__(self, message="interrupted", *, output="", stderr=""):
        super().__init__(message)
        self.output = output
        self.stderr = stderr


def run_bounded(command, *, cwd, input, text=True, capture_output=True, check=False,
                timeout: float, cancel: Event | None = None, grace: float = 2.0):
    if timeout <= 0:
        raise ValueError('execution timeout must be positive')
    if cancel is not None and cancel.is_set():
        raise ExecutionInterrupted('execution cancelled before launch')
    process = subprocess.Popen(command, cwd=cwd, text=text, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    deadline = time.monotonic() + timeout
    first = True
    failure = None
    try:
        while True:
            if cancel is not None and cancel.is_set():
                failure = 'cancelled'
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = 'timeout'
                break
            try:
                stdout, stderr = process.communicate(input if first else None, timeout=min(0.1, remaining))
                return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                first = False
    finally:
        # Terminate the entire original process group, including descendants
        # that retain pipe handles or ignore TERM. This is lifecycle control,
        # not a security sandbox against a process that deliberately escapes.
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass
            if sig == signal.SIGTERM:
                try:
                    process.communicate(timeout=grace)
                except subprocess.TimeoutExpired:
                    pass
        stdout, stderr = process.communicate()
    if failure == 'cancelled':
        raise ExecutionInterrupted('execution cancelled; workspace preserved', output=stdout, stderr=stderr)
    raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr)
