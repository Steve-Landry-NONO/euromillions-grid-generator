"""Stub pytest minimal pour exécution sans installation."""
import sys

class mark:
    @staticmethod
    def slow(fn): return fn
    @staticmethod
    def skipif(cond, reason=""): 
        def decorator(fn): return fn
        return decorator
    @staticmethod
    def integration(fn): return fn
    @staticmethod
    def unit(fn): return fn

class _ApproxBase:
    def __init__(self, expected, abs=None, rel=None):
        self.expected = expected
        self.abs = abs or 1e-6
    def __eq__(self, actual):
        return abs(actual - self.expected) <= self.abs
    def __repr__(self):
        return f"approx({self.expected})"

def approx(val, abs=None, rel=None):
    return _ApproxBase(val, abs=abs, rel=rel)

def skip(reason=""):
    raise SkipTest(reason)

class SkipTest(Exception):
    pass

class raises:
    def __init__(self, exc_type, match=None):
        self.exc_type = exc_type
        self.match = match
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, tb):
        if exc_type is None:
            raise AssertionError(f"Expected {self.exc_type.__name__} but no exception raised")
        if not issubclass(exc_type, self.exc_type):
            return False  # laisse l'exception se propager
        if self.match:
            import re
            if not re.search(self.match, str(exc_val)):
                raise AssertionError(f"Exception message '{exc_val}' does not match '{self.match}'")
        return True  # supprime l'exception

def fail(msg):
    raise AssertionError(msg)

# Injecter dans sys.modules
sys.modules['pytest'] = sys.modules[__name__]
