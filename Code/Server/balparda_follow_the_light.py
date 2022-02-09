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


_ANGLE_OF_VIEW = (53.5, 41.41)


def _MainPipelines(mock=False):
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
            lambda i: (i[0], i[1], i[1].BrightnessFocus()),  # processing is trivial in fact
            brightness_stop),
      daemon=True)
  # setup moving pipeline (acting on real or mock cars) with its semaphore
  movement_stop = multiprocessing.Value('b', 0, lock=True)
  movement_process = multiprocessing.Process(
      target=lib.UpToDateProcessingPipeline,
      name='movement-pipeline',
      args=(brightness_queue,  # feed from brightness queue
            None,              # end of pipeline, so don't feed a new queue
            _MovementDecisionMaker(mock=mock),  # the actual movement operation goes here
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
      time.sleep(0.3)  # main thread should mostly block here
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


def _MovementDecisionMaker(mock=False):
  """Create a decision maker incorporating either the real or a mock car."""

  class _MockEngine():  # mock car.Engine

    def Straight(self, speed, tm):
      logging.info('Move at speed %d for %0.2f seconds', speed, tm)
      time.sleep(tm)

    def Turn(self, angle):
      logging.info('Turn %0.2f degrees', angle)
      time.sleep(int(abs(angle * (.7/90))))

  class _MockNeck():  # mock car.Neck

    def __init__(self):
      self._pos = (0, 0)

    def Delta(self, servo_dict):
      self._pos = (self._pos[0] + servo_dict['H'], self._pos[1] + servo_dict['V'])
      logging.info('Neck to position %r', self._pos)
      time.sleep(0.2)

  class _MockSonar():  # mock car.Sonar

    def Read(self):
      time.sleep(0.1)
      return 1.0

  engine = _MockEngine() if mock else car.Engine()
  neck = _MockNeck() if mock else car.Neck(offset={'H': 6.0, 'V': -23.0})
  sonar = _MockSonar() if mock else car.Sonar()

  def _MovementDecision(input):
    """Take a "step" movement decision based on a camera and sonar reading."""
    # TODO: maybe move sonar readings into a separate pipeline?
    num_img, img, (x_focus, y_focus) = input
    x_angle, y_angle = img.PointToAngle(x_focus, y_focus, _ANGLE_OF_VIEW[0], _ANGLE_OF_VIEW[1])
    x_angle, y_angle = int(x_angle), int(y_angle)
    dist = sonar.Read()
    logging.info('Got foci for image #%04d: (%d, %d) @ %0.2fm', num_img, x_angle, y_angle, dist)
    neck.Delta({'H': x_angle, 'V': y_angle})

  return _MovementDecision


def main():
  """Execute main method."""
  logging.info('Start')
  try:
    _MainPipelines(mock=_MOCK)
  finally:
    logging.info('End')


if __name__ == '__main__':
  lib.StartMultiprocessing()
  lib.StartStdErrLogging()
  main()
