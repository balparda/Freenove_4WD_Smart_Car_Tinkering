#!/usr/bin/python3 -O
"""Follow-the-Light automaton program for the car."""

_MOCK = True

import logging
import multiprocessing
# import pdb
import time

import balparda_imaging as imaging
import balparda_lib as lib
if not _MOCK:
  import balparda_car as car  # this module will not load on non-Raspberry-Pi machines
else:
  car = None


def MainPipelines(mock=False):
  """Will start image pipelines pipe them into decision pipeline.

  Args:
    mock: (default False) If True will use mock modules that load on regular machines, for testing
  """
  # setup image pipeline (real or mock) with its queue and process semaphore
  img_queue = multiprocessing.JoinableQueue()
  img_stop = multiprocessing.Value('b', 0, lock=True)
  img_process = multiprocessing.Process(
      target=imaging.MockQueueImages if mock else car.QueueImages,
      name='image-pipeline',
      args=((img_queue, img_stop, 'testimg/capture-001-*.jpg', .7) if mock else
            (img_queue, img_stop)),
      daemon=True)
  # setup processing pipeline (feeding real or mock images) with its queue and process semaphore
  brightness_queue = multiprocessing.JoinableQueue()
  brightness_stop = multiprocessing.Value('b', 0, lock=True)
  brightness_process = multiprocessing.Process(
      target=lib.UpToDateProcessingPipeline,
      name='brightness-pipeline',
      args=(img_queue,         # feed from image queue
            brightness_queue,  # write to this new queue
            lambda i: (i[0], i[1], i[1].BrightnessFocus()),
            brightness_stop),
      daemon=True)
  # setup moving pipeline (acting on real or mock cars) with its semaphore
  movement_stop = multiprocessing.Value('b', 0, lock=True)
  movement_process = multiprocessing.Process(
      target=lib.UpToDateProcessingPipeline,
      name='movement-pipeline',
      args=(brightness_queue,  # feed from brightness queue
            None,              # end of pipeline, so don't feed a new queue
            lambda i: i,  # TODO!!
            movement_stop),
      daemon=True)
  # start
  logging.info('Starting pipeline processes: camera, brightness, car movement')
  movement_process.start()
  brightness_process.start()
  img_process.start()
  try:
    # go to sleep while the pipeline does the job or while we wait for a Ctrl-C
    while True:
      time.sleep(0.5)
  finally:
    # signal stop and wait for queues
    img_stop.value = 1
    brightness_stop.value = 1
    movement_stop.value = 1
    logging.info('Waiting for image pipeline')
    img_process.join()
    logging.info('Waiting for processing pipeline')
    brightness_process.join()
    logging.info('Waiting for movement pipeline')
    movement_process.join()


def main():
  """Execute main method."""
  logging.info('Start')
  try:
    MainPipelines(mock=_MOCK)
  finally:
    logging.info('End')


if __name__ == '__main__':
  lib.StartMultiprocessing()
  lib.StartStdErrLogging()
  main()
