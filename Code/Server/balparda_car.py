#!/usr/bin/python3 -O
"""Balparda's car API."""

import io
import logging
import multiprocessing
import multiprocessing.sharedctypes
# import pdb
import time
from typing import Any, Dict, Iterator, Tuple

import picamera  # type: ignore

from Code.Server import ADC
from Code.Server import Buzzer
from Code.Server import Led
from Code.Server import Line_Tracking
from Code.Server import Motor
from Code.Server import servo
from Code.Server import Ultrasonic

from Code.Server import balparda_imaging as imaging


class Battery():
  """Car battery functionality wrapper."""

  _BATTERY_FACTOR = 3.0
  _BATTERY_INDEX = 3

  def __init__(self) -> None:
    """Create object."""
    self._a = ADC.Adc()

  def Read(self) -> float:
    """Return float batery reading, in volts."""
    return Battery._BATTERY_FACTOR * self._a.recvADC(Battery._BATTERY_INDEX)

  def __str__(self) -> str:
    """Print human readable battery reading."""
    return "Battery: %0.2f Volts" % self.Read()

  def __repr__(self) -> str:
    """Representation of float battery reading."""
    return repr(self.Read())


class Photoresistor():
  """Car photoresistor functionality wrapper."""

  _PHOTO_INDEX = (0, 1)

  def __init__(self) -> None:
    """Create object."""
    self._a = ADC.Adc()

  def Read(self) -> Tuple[float, float]:
    """Return left & right (left_float, right_float) photoresistor reading."""
    return (self._a.recvADC(Photoresistor._PHOTO_INDEX[0]),
            self._a.recvADC(Photoresistor._PHOTO_INDEX[1]))

  def __str__(self) -> str:
    """Print human readable left & right photoresistor reading."""
    return "Photoresistor:  Left %0.2f  /  Right %0.2f" % self.Read()

  def __repr__(self) -> str:
    """Representation of (left_float, right_float) photoresistor reading."""
    return repr(self.Read())


class Engine():
  """Car engine (movement) functionality wrapper."""

  _GAIN = 400

  def __init__(self) -> None:
    """Create object."""
    self._m = Motor.Motor()

  def Move(self,
           left_upper: int,
           left_lower: int,
           right_upper: int,
           right_lower: int,
           tm: float) -> None:
    """Move car wheels for a certain time. Will block.

    Args:
      left_upper: Speed to apply to upper left wheel, int, 1 to 10.
      left_lower: Speed to apply to lower left wheel, int, 1 to 10.
      right_upper: Speed to apply to upper right wheel, int, 1 to 10.
      right_lower: Speed to apply to lower right wheel, int, 1 to 10.
      tm: Time to apply motors, in seconds.
    """
    left_upper, left_lower = int(left_upper), int(left_lower)
    right_upper, right_lower = int(right_upper), int(right_lower)
    try:
      self._m.setMotorModel(round(Engine._GAIN * left_upper),
                            round(Engine._GAIN * left_lower),
                            round(Engine._GAIN * right_upper),
                            round(Engine._GAIN * right_lower))
      time.sleep(tm)
    finally:
      self._m.setMotorModel(0, 0, 0, 0)

  def Straight(self, speed: int, tm: float) -> None:
    """Move car ahead at `speed` for `tm` seconds. Will block."""
    speed = int(speed)
    logging.info('Move at speed %d for %0.2f seconds', speed, tm)
    self.Move(speed, speed, speed, speed, tm)

  def Turn(self, angle: int) -> None:
    """Turn car by `angle`. Will block until done.

    Works best when angle is +90 or -90 as car is actually non-linear.
    """
    angle = int(angle)
    logging.info('Turn %d degrees', angle)
    tm = abs(angle * (.7/90))
    if angle > 0:
      self.Move(5, 5, -4, -4, tm)
    else:
      self.Move(-4, -4, 5, 5, tm)


class Noise():
  """Car beeper functionality wrapper. This is a context object."""

  def __init__(self) -> None:
    """Create context object."""
    self._b = Buzzer.Buzzer()

  def __enter__(self) -> Any:
    """Enter context: start making noise."""
    logging.info('Beep!')
    self._b.run('1')
    return self

  def __exit__(self, a, b, c) -> None:
    """Leave context: stop making noise."""
    self._b.run('0')
    logging.info('Silence...')


class Light():
  """Car lighting (leds) functionality wrapper. This is a context object."""

  def __init__(self, led_dict: Dict[int, Tuple[int, int, int]]) -> None:
    """Create context object.

    Args:
      led_dict: like {led_number: (red_uint8, green_uint8, blue_uint8)}
    """
    self._l = Led.Led()
    self._dict = led_dict
    if not self._dict:
      raise Exception('Empty led_dict')

  def __enter__(self) -> Any:
    """Enter context: turn on the leds."""
    logging.info('Lights @ %r', self._dict)
    for n, (r, g, b) in self._dict.items():
      self._l.ledIndex(1 << n, r, g, b)
    return self

  def __exit__(self, a, b, c) -> None:
    """Leave context: turn leds off."""
    self._l.colorWipe(self._l.strip, Led.Color(0, 0, 0))  # type: ignore
    logging.info('Lights off')


class Sonar():
  """Car sonar (distance detection) functionality wrapper."""

  def __init__(self) -> None:
    """Create object."""
    self._s = Ultrasonic.Ultrasonic()

  def Read(self) -> float:
    """Return float distance reading, in meters."""
    return self._s.get_distance() / 100.0

  def __str__(self) -> str:
    """Print human readable distance reading."""
    return "Distance: %0.3f meters" % self.Read()

  def __repr__(self) -> str:
    """Representation of float distance reading."""
    return repr(self.Read())


class Neck():
  """Car neck and head movement functionality wrapper."""

  def __init__(self, offset: Tuple[int, int] = (0, 0)) -> None:
    """Create object.

    Args:
      offset: like (horizontal_offset, vertical_offset), in degrees, default is no offset
    """
    self._s = servo.Servo()
    self._pos = (0, 0)
    if not offset:
      raise Exception('Empty offset')
    self._o = (int(round(offset[0])), int(round(offset[1])))

  def __enter__(self) -> Any:
    """Enter context: reset neck to center."""
    self.Zero()
    return self

  def __exit__(self, a, b, c) -> None:
    """Leave context: reset neck to center."""
    self.Zero()

  def Set(self, h: int, v: int) -> None:
    """Set neck to a position.

    Args:
      h: horizontal angle, in degrees
      v: vertical angle, in degrees
    """
    if h < -70: h = -70  # noqa: E701
    if h > 70:  h = 70   # noqa: E701
    if v < -20: v = -20  # noqa: E701
    if v > 70:  v = 70   # noqa: E701
    logging.info('Neck to position %s', Neck._NECK_POSITION_STR((h, v)))
    self._Set(h, v)

  _MAX_STEP = 3

  def _Set(self, h: int, v: int) -> None:
    new_pos = (int(round(h)), int(round(v)))
    while self._pos[0] != new_pos[0] or self._pos[1] != new_pos[1]:
      hd, vd = new_pos[0] - self._pos[0], new_pos[1] - self._pos[1]
      if abs(hd) > Neck._MAX_STEP:
        hd = Neck._MAX_STEP if hd > 0 else -Neck._MAX_STEP
      if abs(vd) > Neck._MAX_STEP:
        vd = Neck._MAX_STEP if vd > 0 else -Neck._MAX_STEP
      self._pos = (self._pos[0] + hd, self._pos[1] + vd)
      self._s.setServoPwm('0', self._pos[0] + self._o[0] + 90)
      self._s.setServoPwm('1', self._pos[1] + self._o[1] + 90)
      time.sleep(0.02)

  def Zero(self) -> None:
    """Return neck to central position."""
    logging.info('Neck to ZERO/CENTER, offset=%s', Neck._NECK_POSITION_STR(self._o))
    self._Set(0, 0)

  def Delta(self, h: int, v: int) -> None:
    """Apply delta to neck.

    Args:
      h: horizontal delta angle, in degrees
      v: vertical delta angle, in degrees
    """
    self.Set(self._pos[0] + h, self._pos[1] + v)

  _NECK_POSITION_STR = lambda p: '(H: %+02d, V: %+02d) degrees' % p

  def __str__(self) -> str:
    """Readable respresentation of neck position."""
    return Neck._NECK_POSITION_STR(self._pos)

  def Read(self) -> Tuple[int, int]:
    """Get current neck position (h_angle, v_angle) in degrees."""
    return self._pos


class Infra():
  """Car lower infra-red sensor functionality wrapper."""

  def __init__(self) -> None:
    """Create object."""
    self._l = Line_Tracking.Line_Tracking()

  def Read(self) -> Tuple[bool, bool, bool]:
    """Return (left_bool, middle_bool, right_bool) infra-red reading."""
    return (bool(Line_Tracking.GPIO.input(self._l.IR01)),
            bool(Line_Tracking.GPIO.input(self._l.IR02)),
            bool(Line_Tracking.GPIO.input(self._l.IR03)))

  def __str__(self) -> str:
    """Print human readable infra-red left, middle, and right reading."""
    l, m, r = self.Read()
    return "Infrared: [ %s - %s - %s ]" % (
        'LL' if l else '..', 'MM' if m else '..', 'RR' if r else '..')

  def __repr__(self) -> str:
    """Representation of (left_bool, middle_bool, right_bool) battery reading."""
    return repr(self.Read())


class Cam():
  """Car camera functionality wrapper. This is a context object."""

  # this is the size if you ask for a JPG; aspect is 4:3
  _WIDTH = 2592
  _HEIGHT = 1944
  _ASPECT = 4.0 / 3.0
  _DEFAULT_RESOLUTION = (800, 600)
  _DEFAULT_FRAMERATE = 10
  _SLEEP_TO_INIT = 1.5
  _FOCAL_LENGTH = 3.60  # mm (https://www.raspberrypi.com/documentation/accessories/camera.html)
  _SENSOR_SIZE = (3.76, 2.74)     # mm
  _ANGLE_OF_VIEW = (53.50, 41.41)  # degrees

  def __init__(self,
               resolution: Tuple[int, int] = _DEFAULT_RESOLUTION,
               framerate: int = _DEFAULT_FRAMERATE) -> None:
    """Create context object.

    Args:
      resolution: (default 800x600) like (width, height) as ints
      framerate: (default 10) int framerate
    """
    self._c: picamera.Picamera
    self._c = None  # type: ignore
    self._resolution = resolution
    self._framerate = framerate

  def __enter__(self) -> Any:
    """Enter context: initialize the camera. ATTENTION: will block for 1.5 seconds."""
    self._c = picamera.PiCamera(resolution=self._resolution, framerate=self._framerate)
    logging.info(
        'Starting camera with resolution %r and framerate %d (+wait %0.2fs)',
        self._resolution, self._framerate, Cam._SLEEP_TO_INIT)
    time.sleep(Cam._SLEEP_TO_INIT)
    return self

  def __exit__(self, a, b, c) -> None:
    """Leave context: close camera object."""
    if not self._c:
      raise Exception('Not initialized')
    self._c.close()
    logging.info('Camera closed')

  def Click(self) -> Tuple[imaging.Image, bytes]:
    """Take a single image.

    Returns:
      (image_object, image_bytes)
    """
    if not self._c:
      raise Exception('Not initialized')
    stream = io.BytesIO()
    self._c.capture(stream, format='bmp')
    stream.seek(0)
    data = stream.read()
    img = imaging.Image(data)
    return (img, data)

  def Stream(self) -> Iterator[Tuple[imaging.Image, bytes]]:
    """Stream images.

    Yields:
      (image_object, image_bytes)
    """
    stream = io.BytesIO()
    logging.info('Camera taking continuous bmp images')
    for _ in self._c.capture_continuous(stream, format='bmp'):
      stream.truncate()  # in case prior iterations output a longer image (unexpected!)
      stream.seek(0)     # rewind to start reading
      data = stream.read()
      img = imaging.Image(data)
      yield (img, data)
      stream.seek(0)  # if we don't rewind again capture_continuous() will write at the end


def QueueImages(queue: multiprocessing.JoinableQueue,
                stop_flag: multiprocessing.sharedctypes.Synchronized) -> None:
  """Define a subprocess for streaming images continuously.

  Expects to be the entry point for a multiprocessing.Process() call. Will write to `queue`
  continuously until `stop_flag` becomes !=0 (True).

  Args:
    queue: a multiprocessing.Queue object that will receive (n, img) tuples, where n is the
        image counter and img is the Nth imaging.Image object
    stop_flag: a multiprocessing.Value('b', 0, lock=True) byte ('b' signed char) object that
        should start 0 (False) and become 1 (True) when the process should end.
  """
  logging.info('Starting image capture pipeline')
  with Cam() as cam:
    for n, (img, _) in enumerate(cam.Stream()):
      if stop_flag.value:
        break
      logging.debug('Capture image #%04d', n)
      queue.put((n, img))
  logging.info('Image capture pipeline stopped')
