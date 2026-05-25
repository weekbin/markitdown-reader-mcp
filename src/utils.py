"""Utility functions for markitdown-reader."""

import resource


def mem():
    """Return memory usage in MB (max RSS / 1024)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
