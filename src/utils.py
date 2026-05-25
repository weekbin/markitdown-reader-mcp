"""Utility functions for markitdown-reader."""

import gc
import resource


def mem():
    """Return memory usage in MB (max RSS / 1024)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024


def _mem_monitor(func_name: str):
    """Print formatted memory stats and return RSS value.

    Output format: [MEM] func_name: rss=XXMB gc_objects=XXXX delta=+XMB
    """
    rss = mem()
    gc_count = sum(gc.get_count())
    print(f"[MEM] {func_name}: rss={rss}MB gc_objects={gc_count} delta=+0MB")
    return rss


class _gc_track:
    """Context manager that logs memory delta on function entry/exit."""

    def __init__(self, func_name: str):
        self.func_name = func_name
        self.entry_rss = None

    def __enter__(self):
        self.entry_rss = _mem_monitor(self.func_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        exit_rss = mem()
        gc_count = sum(gc.get_count())
        delta = exit_rss - self.entry_rss
        print(f"[MEM] {self.func_name}: rss={exit_rss}MB gc_objects={gc_count} delta={delta:+d}MB")
