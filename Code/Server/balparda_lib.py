#!/usr/bin/python3 -O
"""Balparda's utils lib."""

# import pdb
import time


class Timer():
  """Time execution."""

  def __init__(self):
    """Create context object."""
    self._t = None

  def __enter__(self):
    """Enter context: get start time."""
    self._t = time.time()
    return self

  def __exit__(self, a, b, c):
    """Leave context: stop timer by printing value."""
    print('Execution time: %0.2f seconds' % (time.time() - self._t))


def Timed(func):
  """Make any call print its execution time if used as a decorator."""
  def _wrapped_call(*args, **kwargs):
    with Timer():
      return func(*args, **kwargs)
  return _wrapped_call
