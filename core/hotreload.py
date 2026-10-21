"""core/hotreload.py - lightweight file watcher for plugins/actions.

Polls directories for mtime changes and invokes a callback. Used to reload
plugins/actions without restarting the app. Deliberately polling (not
watchdog) so it works on every OS without an extra dependency.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable


class FileWatcher:
    def __init__(self, dirs: list[Path], callback: Callable[[], None],
                 interval: float = 5.0):
        self.dirs = [Path(d) for d in dirs]
        self.callback = callback
        self.interval = interval
        self._mtimes: dict[str, float] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._snapshot()

    def _snapshot(self) -> dict[str, float]:
        out = {}
        for d in self.dirs:
            if not d.exists():
                continue
            for p in d.glob("*.py"):
                try:
                    out[str(p)] = p.stat().st_mtime
                except OSError:
                    pass
        return out

    def _changed(self) -> bool:
        new = self._snapshot()
        if new != self._mtimes:
            self._mtimes = new
            return True
        return False

    def start(self) -> None:
        if self._thread is not None:
            return
        self._mtimes = self._snapshot()

        def loop():
            while not self._stop.is_set():
                time.sleep(self.interval)
                try:
                    if self._changed():
                        self.callback()
                except Exception as e:
                    print(f"[HotReload] callback failed: {e}")

        self._thread = threading.Thread(target=loop, daemon=True, name="hotreload")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
