#!/usr/bin/python3 -O
"""Follow-the-Light automaton program for the car."""

# noqa: E402

_MOCK = True

import logging          # noqa: E402
import multiprocessing  # noqa: E402
import multiprocessing.sharedctypes  # noqa: E402
# import pdb
import time  # noqa: E402
from typing import Callable, Tuple  # noqa: E402

from Code.Server import balparda_imaging as imaging  # noqa: E402
from Code.Server import balparda_lib as lib          # noqa: E402
if not _MOCK:
  from Code.Server import balparda_car as car  # will not load on non-Raspberry-Pi machines
else:
  car = None  # type: ignore


_ANGLE_OF_VIEW = (53.5, 41.41)
_NECK_OFFSET = (6, -30)
_MIN_SONAR_DISTANCE = 0.20
_V_ANGLE = 45
_ANGLE_TARGET_PRECISION = 5
_CAR_SPEED = 1
_CAR_MOVE_INCREMENT_TIME = 0.5
_MOCK_TEMPLATE = 'Code/Server/testimg/capture-001-*.jpg'
_SAVE_TEMPLATE = 'Code/Server/testimg/capture-002-%03d.jpg'


def _MainPipelines(mock: bool = False) -> None:
  """Will start image pipelines pipe them into decision pipeline.

  Args:
    mock: (default False) If True will use mock modules that load on regular machines, for testing
  """
  # setup image pipeline (real or mock) with its queue and process semaphore
  img_queue = multiprocessing.JoinableQueue()  # type: multiprocessing.JoinableQueue
  img_stop: multiprocessing.sharedctypes.Synchronized
  img_stop = multiprocessing.Value('b', 0, lock=True)  # type: ignore
  img_process = multiprocessing.Process(
      target=imaging.MockQueueImages if mock else car.QueueImages,
      name='image-pipeline',
      args=((img_queue, img_stop, _MOCK_TEMPLATE, .7) if mock else
            (img_queue, img_stop)),
      daemon=True)
  # setup processing pipeline (feeding real or mock images) with its queue and process semaphore
  brightness_queue = multiprocessing.JoinableQueue()  # type: multiprocessing.JoinableQueue
  brightness_stop: multiprocessing.sharedctypes.Synchronized
  brightness_stop = multiprocessing.Value('b', 0, lock=True)  # type: ignore
  brightness_process = multiprocessing.Process(
      target=lib.UpToDateProcessingPipeline,
      name='brightness-pipeline',
      args=(img_queue,         # feed from image queue
            brightness_queue,  # write to this new queue
            lambda i: (i[0], i[1], i[1].BrightnessFocus()),  # processing is trivial in fact
            brightness_stop),
      daemon=True)
  # setup moving pipeline (acting on real or mock cars) with its semaphore
  movement_stop: multiprocessing.sharedctypes.Synchronized
  movement_stop = multiprocessing.Value('b', 0, lock=True)  # type: ignore
  movement_process = multiprocessing.Process(
      target=lib.UpToDateProcessingPipeline,
      name='movement-pipeline',
      args=(brightness_queue,  # feed from brightness queue
            None,              # end of pipeline, so don't feed a new queue
            _MovementDecisionMaker(desired_v_angle=_V_ANGLE, mock=mock),  # atual movement operation
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


def _MovementDecisionMaker(desired_v_angle: int = 45, mock: bool = False) -> Callable:
  """Create a decision maker incorporating either the real or a mock car.

  Args:
    desired_v_angle: (default 45) vertical angle the car will try to keep constant
    mock: (default False) if True will use mock car classes that don't require hardware to run
  """

  class _MockEngine():  # mock car.Engine

    def Straight(self, speed: int, tm: float) -> None:
      logging.info('Move at speed %d for %0.2f seconds', speed, tm)
      time.sleep(tm)

    def Turn(self, angle: int) -> None:
      logging.info('Turn %0.2f degrees', angle)
      time.sleep(int(abs(angle * (.7/90))))

  class _MockNeck():  # mock car.Neck

    def __init__(self) -> None:
      self._pos = (0, 0)

    def Zero(self) -> None:
      self._pos = (0, 0)
      logging.info('Neck to ZERO/CENTER')

    def Delta(self, h: int, v: int) -> None:
      h, v = self._pos[0] + h, self._pos[1] + v
      if h < -70: h = -70  # noqa: E701
      if h > 70:  h = 70   # noqa: E701
      if v < -20: v = -20  # noqa: E701
      if v > 70:  v = 70   # noqa: E701
      self._pos = (h, v)
      logging.info('Neck to position (H: %+02d, V: %+02d) degrees', h, v)
      time.sleep(0.3)

    def Read(self) -> Tuple[int, int]:
      return self._pos

  class _MockSonar():  # mock car.Sonar

    def Read(self) -> float:
      time.sleep(0.1)
      return 1.0

  engine: _MockEngine
  sonar: _MockSonar
  neck: _MockNeck
  engine = _MockEngine() if mock else car.Engine()               # type: ignore
  sonar = _MockSonar() if mock else car.Sonar()                  # type: ignore
  neck = _MockNeck() if mock else car.Neck(offset=_NECK_OFFSET)  # type: ignore
  neck.Zero()

  def _MovementDecision(input: Tuple[int, imaging.Image, Tuple[int, int]]) -> None:
    """Take a "step" movement decision based on a camera and sonar reading."""
    # TODO: maybe move sonar readings into a separate pipeline? Is it even needed? Test sonar speed.
    num_img, img, (x_focus, y_focus) = input
    # img.Save(_SAVE_TEMPLATE % num_img)  # uncomment to save the stream for testing...
    # convert the point we got into angles as seen by the camera, then point the camera there
    x_angle, y_angle = img.PointToAngle(x_focus, y_focus, _ANGLE_OF_VIEW[0], _ANGLE_OF_VIEW[1])
    x_angle, y_angle = int(x_angle), int(y_angle)
    dist = sonar.Read()
    logging.info('Got foci for image #%04d: (%d, %d) @ %0.2fm', num_img, x_angle, y_angle, dist)
    neck.Delta(x_angle, y_angle)
    # now that neck moved we read the position to determine where to move the body of the car()
    # we first correct for horizontal deviation and then decide to move either way
    h, v = neck.Read()
    if abs(h) > _ANGLE_TARGET_PRECISION:  # need to turn?
      engine.Turn(h)
    if dist < _MIN_SONAR_DISTANCE:  # if we are too close to an obstacle we go back
      engine.Straight(-_CAR_SPEED, _CAR_MOVE_INCREMENT_TIME)
    else:
      if abs(desired_v_angle - v) > _ANGLE_TARGET_PRECISION:  # need to move?
        engine.Straight(_CAR_SPEED if desired_v_angle > v else -_CAR_SPEED,
                        _CAR_MOVE_INCREMENT_TIME)

  return _MovementDecision


def main() -> None:
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
