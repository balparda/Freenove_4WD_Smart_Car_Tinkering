#!/usr/bin/python3 -O
"""Balparda's utils lib."""

import logging
import multiprocessing
import multiprocessing.sharedctypes
# import pdb
import time
import sys
from typing import Any, Callable


_LOG_FORMATS = (
    '%(asctime)s.%(msecs)03d%(levelname)08s[%(funcName)s]: %(message)s',  # without process name
    '%(asctime)s.%(msecs)03d%(levelname)08s[%(processName)s.%(funcName)s]: %(message)s',  # with prc
    '%Y%m%d.%H:%M:%S',  # date format
)
# example '20220209.14:16:47.667    INFO[SomeMethodName]: Some message'


def StartMultiprocessing(method: str = 'fork') -> None:
  """Start multiprocessing by setting up method.

  Should be called only once like  `if __name__ == '__main__': lib.StartMultiprocessing(); main()`.

  Args:
    method: (default 'fork') Method to use
  """
  multiprocessing.set_start_method(method)


def StartStdErrLogging(level: int = logging.INFO, logprocess: bool = False) -> None:
  """Start logging to stderr.

  Should be called only once like  `if __name__ == '__main__': lib.StartStdErrLogging(); main()`.

  Args:
    level: (default logging.INFO) logging level to use
    logprocess: (default False) If True will add process names to log strings (as in the process
        `multiprocessing.Process(name=[somename])` call)
  """
  logger = logging.getLogger()
  logger.setLevel(level)
  handler = logging.StreamHandler(sys.stdout)
  handler.setLevel(level)
  formatter = logging.Formatter(
      fmt=_LOG_FORMATS[1] if logprocess else _LOG_FORMATS[0],
      datefmt=_LOG_FORMATS[2])
  handler.setFormatter(formatter)
  logger.addHandler(handler)


class Timer():
  """Time execution."""

  def __init__(self) -> None:
    """Create context object."""
    self._t = 0.0

  def __enter__(self) -> Any:
    """Enter context: get start time."""
    self._t = time.time()
    return self

  def __exit__(self, a, b, c) -> None:
    """Leave context: stop timer by printing value."""
    logging.warning('Execution time: %0.2f seconds', time.time() - self._t)


def Timed(func: Callable):
  """Make any call print its execution time if used as a decorator."""
  def _wrapped_call(*args, **kwargs):
    with Timer():
      return func(*args, **kwargs)
  return _wrapped_call


def MinAngle(angle: int, allow_neg: bool = True) -> int:
  """Make sure any int angle always reduced to minimum bounds.

  Args:
    angle: the angle in degrees
    allow_neg: (default True) if True returned angle will be between -179 and 180 inclusive;
        if False returned angle will be between 0 and 359 inclusive

  Returns:
    the `angle` reduced to either [-179,180] or [0,359], depending on `allow_neg`
  """
  angle = ((int(angle) % 360) + 360) % 360  # guaranteed 0 <= angle <= 359
  return angle if not allow_neg or angle <= 180 else (angle - 360)


def UpToDateProcessingPipeline(input_queue: multiprocessing.JoinableQueue,
                               output_queue: multiprocessing.JoinableQueue,
                               process_call: Callable,
                               stop_flag: multiprocessing.sharedctypes.Synchronized,
                               pipeline_name: str = '') -> None:
  """Define a subprocess for processing continuously from `input_queue` to `output_queue`.

  Expects to be the entry point for a multiprocessing.Process() call. Will process items by
  calling `process_call()` continuously until `stop_flag` becomes !=0 (True). Will try to always
  keep up-to-date by skipping objects in `input_queue` if they come faster than the processing
  is taking, i.e., NOT ALL objects in `input_queue` will be processed! Also, there CANNOT be
  any other consumer of `input_queue` elements.

  multiprocessing.Queue.qsize() is said to be unreliable:
  https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Queue.qsize
  but "supported" get_nowait()->raise and get(timeout=0.05) will not consistently extract all
  queue elements.

  Args:
    input_queue: a multiprocessing.Queue object to be read from; NOT ALL objects will be processed
    output_queue: a multiprocessing.Queue object to be writen to; can be `None` and then values
        from `process_call()` will be discarded (i.e. this process will be the end of a pipeline)
    process_call: a method call that takes objects from `input_queue` type and returns objects of
        `output_queue` type
    stop_flag: a multiprocessing.Value('b', 0, lock=True) byte ('b' signed char) object that
        should start 0 (False) and become 1 (True) when the process should end.
    pipeline_name: (default '') If given, is a string process name, just for logging/debugging
  """
  pipeline_str = (' [%s]' % pipeline_name.strip()) if pipeline_name.strip() else ''

  def _patient_discarding_pickup() -> Any:
    # first wait for something in the queue by poling... remember to allow for stop flag
    while not input_queue.qsize():
      if stop_flag.value:
        return None
      time.sleep(0.005)
    # we should have something, reduce size to 1
    sz = input_queue.qsize()
    while sz:
      # we are going to asssume the queue has *at least* sz elements; first discard extra ones
      if sz > 1:
        logging.debug('Discarding %d tasks%s', sz - 1, pipeline_str)
        for _ in range(sz - 1):
          input_queue.get()  # discard value
          input_queue.task_done()
      # we *should* have only one left in queue
      obj = input_queue.get()
      sz = input_queue.qsize()
      if sz:
        # this probably means we had elements added while we waited; mark done and try again
        logging.debug('Discarding 1 (tentative) task%s', pipeline_str)
        input_queue.task_done()  # if we know the loop will try again, we have to discard
    return obj

  # main loop of picking up tasks and working on them
  logging.info('Processing pipeline starting%s', pipeline_str)
  n = 0
  try:
    while True:
      task = _patient_discarding_pickup()
      if task is None:
        break  # this means stop_flag.value is True, so exit
      try:
        if stop_flag.value:  # we might have gotten a stop flag during get()s
          break
        logging.debug('Task #%04d is processing%s', n, pipeline_str)
        result = process_call(task)
        if output_queue is not None:
          output_queue.put(result)
        n += 1
      finally:
        input_queue.task_done()
  finally:
    # we need to finish consuming the queue now
    if input_queue.qsize():
      logging.debug('Discarding %d remaining tasks%s', input_queue.qsize(), pipeline_str)
    while input_queue.qsize():
      input_queue.get()  # discard value
      input_queue.task_done()
    logging.info('Processing pipeline ending%s', pipeline_str)
