"""Provider composition boundary; the worker core does not construct adapters."""
from threading import Event
from .provider import Provider


def create_provider(name: str, *, timeout_seconds: int, cancel: Event) -> Provider:
    if name == 'codex':
        from .codex_runner import CodexRunner
        return CodexRunner(timeout_seconds=timeout_seconds, cancel=cancel)
    raise ValueError('unsupported provider')
