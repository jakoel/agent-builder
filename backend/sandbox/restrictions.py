"""Sandbox restriction primitives: import blocklist, blocked builtins, and the
restriction header that gets prepended to every tool execution."""

# Modules that are explicitly BLOCKED — everything else is allowed.
# The subprocess itself is the primary sandbox boundary; this is defense-in-depth.
BLOCKED_MODULES: list[str] = [
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "importlib",
    "ctypes",
    "signal",
    "multiprocessing",
    "threading",
    "code",
    "pickle",
    "shelve",
    "sqlite3",
    "pathlib",
    "tempfile",
    "glob",
    "webbrowser",
    "http.server",
    "xmlrpc",
    "ftplib",
    "smtplib",
    "telnetlib",
]

BLOCKED_BUILTINS: list[str] = [
    "breakpoint",
    "exit",
    "quit",
    "open",
    "input",
]


def generate_restriction_header() -> str:
    """Return a Python code snippet that installs an import hook blocking
    dangerous modules and removes dangerous builtins."""

    blocked_repr = repr(BLOCKED_MODULES)
    builtins_repr = repr(BLOCKED_BUILTINS)

    return f'''\
import sys as _sys

# Pre-import libs that pull in threading/logging as side-effects before the blocker installs
try:
    import logging as _logging_preload  # noqa: F401
    import urllib3 as _urllib3_preload  # noqa: F401
    import requests as _requests_preload  # noqa: F401
except Exception:
    pass

# ---- import restriction hook ------------------------------------------------
class _ImportBlocker:
    """Meta-path finder that blocks dangerous imports."""
    _blocked = {blocked_repr}

    def find_module(self, fullname, path=None):
        top = fullname.split(".")[0]
        if top in self._blocked or fullname in self._blocked:
            return self
        return None

    def load_module(self, fullname):
        raise ImportError(f"Import of '{{fullname}}' is not allowed in the sandbox")

_sys.meta_path.insert(0, _ImportBlocker())

# ---- builtin restrictions ---------------------------------------------------
_blocked_builtins = {builtins_repr}
for _name in _blocked_builtins:
    if isinstance(__builtins__, dict):
        if _name in __builtins__:
            __builtins__[_name] = None
    else:
        if hasattr(__builtins__, _name):
            setattr(__builtins__, _name, None)

# Remove helpers from the namespace
del _sys, _blocked_builtins, _name, _ImportBlocker
'''
