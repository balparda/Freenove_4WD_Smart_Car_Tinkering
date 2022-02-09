#!/usr/bin/python3 -O
"""Balparda's utils lib."""

import logging
import pdb
import time
import sys


_LOG_FORMAT = (
    '%(asctime)s.%(msecs)03d%(levelname)08s[%(funcName)s]: %(message)s',  # global format
    '%Y%m%d.%H:%M:%S',  # date format
)
# example '20220209.14:16:47.667    INFO[SomeMethodName]: Some message'


def StartStdErrLogging(level):
  """Setup logging to stderr."""
  logger = logging.getLogger()
  logger.setLevel(level)
  handler = logging.StreamHandler(sys.stdout)
  handler.setLevel(level)
  formatter = logging.Formatter(fmt=_LOG_FORMAT[0], datefmt=_LOG_FORMAT[1])
  handler.setFormatter(formatter)
  logger.addHandler(handler)


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
    logging.info('Execution time: %0.2f seconds', time.time() - self._t)


def Timed(func):
  """Make any call print its execution time if used as a decorator."""
  def _wrapped_call(*args, **kwargs):
    with Timer():
      return func(*args, **kwargs)
  return _wrapped_call


def UpToDateProcessingPipeline(input_queue, output_queue, process_call, stop_flag):
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
    input_queue: a multiprocessing.Queue object to be write to
    process_call: a method call that takes objects from `input_queue` type and returns objects of
        `output_queue` type
    stop_flag: a multiprocessing.Value('b', 0, lock=True) byte ('b' signed char) object that
        should start 0 (False) and become 1 (True) when the process should end.
  """

  def _patient_discarding_pickup():
    # first wait for something in the queue by poling...
    while not input_queue.qsize():
      if stop_flag.value:
        return None
      time.sleep(0.005)
    # we should have something, reduce size to 1
    sz = input_queue.qsize()
    while sz:
      # we are going to asssume the queue has *at least* sz elements; first discard extra ones
      if sz > 1:
        logging.info('Discarding %d tasks', sz - 1)
        for _ in range(sz - 1):
          input_queue.get()  # discard value
          input_queue.task_done()
      # we *should* have only one left in queue
      obj = input_queue.get()
      sz = input_queue.qsize()
      if sz:
        # this probably means we had elements added while we waited; mark done and try again
        logging.info('Discarding 1 (tentative) task')
        input_queue.task_done()  # if we know the loop will try again, we have to discard
    return obj

  # main loop of picking up tasks and working on them
  logging.info('Processing pipeline starting')
  n = 0
  try:
    while True:
      task = _patient_discarding_pickup()
      if task is None:
        break  # this means stop_flag.value is True, so exit
      try:
        if stop_flag.value:
          break
        logging.info('Task #%04d is processing', n)
        output_queue.put(process_call(task))
        n += 1
      finally:
        input_queue.task_done()
  finally:
    # we need to finish consuming the queue now
    if input_queue.qsize():
      logging.info('Discarding %d remaining tasks', input_queue.qsize())
    while input_queue.qsize():
      input_queue.get()  # discard value
      input_queue.task_done()
    logging.info('Processing pipeline ending')
