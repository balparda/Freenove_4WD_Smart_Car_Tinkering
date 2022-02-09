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


def UpToDateProcessingPipeline(input_queue, output_queue, process_call, stop_flag):
  """Define a subprocess for processing continuously from `input_queue` to `output_queue`.

  Expects to be the entry point for a multiprocessing.Process() call. Will process items by
  calling `process_call()` continuously until `stop_flag` becomes !=0 (True). Will try to always
  keep up-to-date by skipping objects in `input_queue` if they come faster than the processing
  is taking, i.e., NOT ALL objects in `input_queue` will be processed! Also, there CANNOT be
  any other consumer of `input_queue` elements.

  multiprocessing.Queue.qsize() is said to be unreliable:
  https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Queue.qsize
  but "saupported" get()->raise and get(timeout=0.05) will not consistently extract all
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
    # first wait for something in the queue
    while not input_queue.qsize():
      if stop_flag.value:
        return None
      print('PP: sleep')
      time.sleep(0.5)
    # we should have something, reduce size to 1
    sz = input_queue.qsize()
    while sz:
      # we are going to asssume the queue has *at least* sz elements
      if sz > 1:
        for _ in range(sz - 1):
          print('PP: discard [1]')
          input_queue.get()  # discard value
          input_queue.task_done()
      print('PP: get')
      obj = input_queue.get()
      print('PP: got img #%d' % obj[0])
      sz = input_queue.qsize()
      if sz:
        print('PP: discard [2]')
        input_queue.task_done()  # if we know the loop will try again, we have to discard
    return obj

    n = 0
    while True:
      task = _patient_discarding_pickup()
      if task is None:
        break
      try:
        print('PP: put %d' % n)
        output_queue.put(process_call(task))
        n += 1
      finally:
        input_queue.task_done()
    print('PP: END')
