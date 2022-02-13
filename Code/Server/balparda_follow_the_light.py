#!/usr/bin/python3 -O
"""Follow-the-Light automaton program for the car."""

_MOCK = True

import logging          # noqa: E402
import multiprocessing  # noqa: E402
import multiprocessing.sharedctypes  # noqa: E402
# import pdb                           # noqa: E402
import time  # noqa: E402
from typing import Callable, Tuple  # noqa: E402

from Code.Server import balparda_imaging as imaging  # noqa: E402
from Code.Server import balparda_lib as lib          # noqa: E402
if not _MOCK:
  from Code.Server import balparda_car as car  # will not load on non-Raspberry-Pi machines
else:
  car = None  # type: ignore


_MAX_RUNTIME = 180.0            # seconds
_ANGLE_OF_VIEW = (53.5, 41.41)  # degrees
_NECK_OFFSET = (6, -30)         # degrees
_MIN_SONAR_DISTANCE = 0.20      # meters
_V_ANGLE = 45                   # degrees
_ANGLE_TARGET_PRECISION = 5     # degrees
_CAR_SPEED = 1
_CAR_MOVE_INCREMENT_TIME = 0.5  # seconds
_MOCK_TEMPLATE = 'Code/Server/testimg/capture-001-*.jpg'
_SAVE_TEMPLATE = 'Code/Server/testimg/capture-002-%03d.jpg'


def _MainPipelines(max_runtime: float = 3600.0, mock: bool = False) -> None:
  """Will start image pipelines pipe them into decision pipeline.

  Args:
    max_runtime: (default 3600.0s, 1 hour) The max time, in seconds, the main loop will run
    mock: (default False) If True will use mock modules that load on regular machines, for testing
  """
  max_runtime = float(max_runtime)
  if max_runtime < 1.0:
    raise Exception('max_runtime must be at least 1.0 (got %f)' % max_runtime)
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
            brightness_stop,
            'brightness-pipeline'),
      daemon=True)
  # setup decision and neck (real or mock) pipeline with its semaphore
  motor_queue = multiprocessing.JoinableQueue()  # type: multiprocessing.JoinableQueue
  decision_stop: multiprocessing.sharedctypes.Synchronized
  decision_stop = multiprocessing.Value('b', 0, lock=True)  # type: ignore
  decision_process = multiprocessing.Process(
      target=lib.UpToDateProcessingPipeline,
      name='decision-pipeline',
      args=(brightness_queue,  # feed from brightness queue
            None,              # end of pipeline, so don't feed a new queue
            _MovementDecisionMaker(motor_queue,  # atual movement decision operation
                                   desired_v_angle=_V_ANGLE,
                                   mock=mock),
            decision_stop,
            'decision-pipeline'),
      daemon=True)
  # setup motor wheel moving pipeline (acting on real or mock cars) with its semaphore
  motor_stop: multiprocessing.sharedctypes.Synchronized
  motor_stop = multiprocessing.Value('b', 0, lock=True)  # type: ignore
  motor_process = multiprocessing.Process(
      target=lib.UpToDateProcessingPipeline,
      name='motor-pipeline',
      args=(motor_queue,  # feed from motor queue
            None,         # end of pipeline, so don't feed a new queue
            _MotorActuatorMaker(mock=mock),  # atual motor operation
            motor_stop,
            'motor-pipeline'),
      daemon=True)
  # start
  ini_tm, runtime = time.time(), 0.0
  logging.info(
      'Starting pipeline processes: camera, brightness, decision, neck & motor (@%0.2f)', ini_tm)
  decision_process.start()
  brightness_process.start()
  img_process.start()
  motor_process.start()
  try:
    # sleep while the pipeline does the job, or while we wait for a Ctrl-C, or while we count time
    while runtime < max_runtime:
      time.sleep(0.3)  # main thread should mostly block here
      runtime = time.time() - ini_tm
  finally:
    # signal stop and wait for queues
    logging.info('End signal (@%0.2f seconds runtime). Waiting for image pipeline', runtime)
    img_stop.value = 1
    brightness_stop.value = 1
    decision_stop.value = 1
    motor_stop.value = 1
    img_process.join()
    logging.info('Waiting for processing pipeline')
    brightness_process.join()
    logging.info('Waiting for decision pipeline')
    decision_process.join()
    logging.info('Waiting for motor pipeline')
    motor_process.join()


def _MovementDecisionMaker(motor_queue: multiprocessing.JoinableQueue,
                           desired_v_angle: int = 45,
                           mock: bool = False) -> Callable:
  """Create a decision maker incorporating either the real or a mock car.

  Args:
    motor_queue: a multiprocessing.Queue object to write to
    desired_v_angle: (default 45) vertical angle the car will try to keep constant
    mock: (default False) if True will use mock car classes that don't require hardware to run
  """

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
      time.sleep(0.5)

    def Read(self) -> Tuple[int, int]:
      return self._pos

  class _MockSonar():  # mock car.Sonar

    def Read(self) -> float:
      time.sleep(0.1)
      return 1.0

  sonar: _MockSonar
  neck: _MockNeck
  sonar = _MockSonar() if mock else car.Sonar()                  # type: ignore
  neck = _MockNeck() if mock else car.Neck(offset=_NECK_OFFSET)  # type: ignore
  neck.Zero()

  def _MovementDecision(input: Tuple[int, imaging.Image, Tuple[int, int]]) -> None:
    """Take a "step" movement decision based on a camera and sonar reading."""
    # TODO: maybe move sonar readings into a separate pipeline? Is it even needed? Test sonar speed.
    num_img, img, (x_focus, y_focus) = input
    # img.Save(_SAVE_TEMPLATE % num_img)  # uncomment to save the stream for testing...
    # convert the point we got into angles as seen by the camera so we can plan to move the neck
    x_angle, y_angle = img.PointToAngle(x_focus, y_focus, _ANGLE_OF_VIEW[0], _ANGLE_OF_VIEW[1])
    x_angle, y_angle = lib.MinAngle(int(round(x_angle))), lib.MinAngle(int(round(y_angle)))
    dist = sonar.Read()
    logging.info('Got foci for image #%04d: (%d, %d) @ %0.2fm', num_img, x_angle, y_angle, dist)
    if abs(x_angle) < _ANGLE_TARGET_PRECISION: x_angle = 0  # noqa: E701
    if abs(y_angle) < _ANGLE_TARGET_PRECISION: y_angle = 0  # noqa: E701
    h, v = neck.Read()
    h, v = h + x_angle, v + y_angle  # (h, v) is the predicted neck position after the neck move
    # we now make the body (motor) moving decisions
    move, move_angle, move_speed = False, 0, 0.0
    if abs(h) >= _ANGLE_TARGET_PRECISION:  # need to turn?
      move, move_angle = True, h
    if dist < _MIN_SONAR_DISTANCE:  # if we are too close to an obstacle we go back
      logging.info('Obstacle detected')
      move, move_speed = True, -_CAR_SPEED
    else:
      if abs(desired_v_angle - v) >= _ANGLE_TARGET_PRECISION:  # need to move?
        move, move_speed = True, _CAR_SPEED * (1 if desired_v_angle > v else -1)
    # if we are going to move the car, then dispatch that to the body moving pipeline
    if move:
      motor_queue.put((move_angle, move_speed))
    else:
      logging.info('Car is on target')
    # now that we dispatched that order, we move the neck in parallel
    if x_angle or y_angle:
      neck.Delta(x_angle, y_angle)
    else:
      logging.info('Neck is on target')

  return _MovementDecision


def _MotorActuatorMaker(mock: bool = False) -> Callable:
  """Create a motor actuator incorporating either the real or a mock car.

  Args:
    mock: (default False) if True will use mock car classes that don't require hardware to run
  """

  class _MockEngine():  # mock car.Engine

    def Straight(self, speed: float, tm: float) -> None:
      logging.info('Move at speed %d for %0.2f seconds', speed, tm)
      time.sleep(tm)

    def Turn(self, angle: int) -> None:
      logging.info('Turn %0.2f degrees', angle)
      time.sleep(int(abs(angle * (.7/90))))

  engine: _MockEngine
  engine = _MockEngine() if mock else car.Engine()  # type: ignore

  def _MotorActuator(input: Tuple[int, float]) -> None:
    """Execute a "step" motor action."""
    move_angle, move_speed = input
    if move_angle:
      engine.Turn(move_angle)
    if abs(move_speed) > 0.01:
      engine.Straight(move_speed, _CAR_MOVE_INCREMENT_TIME)

  return _MotorActuator


def main() -> None:
  """Execute main method."""
  logging.info('Start')
  try:
    _MainPipelines(max_runtime=_MAX_RUNTIME, mock=_MOCK)
  finally:
    logging.info('End')


if __name__ == '__main__':
  lib.StartMultiprocessing()
  lib.StartStdErrLogging()
  main()
