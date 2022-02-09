#!/usr/bin/python3 -O
"""Balparda's car API."""

import io
import logging
# import pdb
import time

# from PIL import Image

import ADC
import Buzzer
import Led
import Line_Tracking
import Motor
import picamera
import servo
import Ultrasonic

import balparda_imaging as imaging


class Battery():
  """Car battery functionality wrapper."""

  _BATTERY_FACTOR = 3.0
  _BATTERY_INDEX = 3

  def __init__(self):
    """Create object."""
    self._a = ADC.Adc()

  def Read(self):
    """Return float batery reading, in volts."""
    return Battery._BATTERY_FACTOR * self._a.recvADC(Battery._BATTERY_INDEX)

  def __str__(self):
    """Print human readable battery reading."""
    return "Battery: %0.2f Volts" % self.Read()

  def __repr__(self):
    """Representation of float battery reading."""
    return repr(self.Read())


class Photoresistor():
  """Car photoresistor functionality wrapper."""

  _PHOTO_INDEX = (0, 1)

  def __init__(self):
    """Create object."""
    self._a = ADC.Adc()

  def Read(self):
    """Return left & right (left_float, right_float) photoresistor reading."""
    return (self._a.recvADC(Photoresistor._PHOTO_INDEX[0]),
            self._a.recvADC(Photoresistor._PHOTO_INDEX[1]))

  def __str__(self):
    """Print human readable left & right photoresistor reading."""
    return "Photoresistor:  Left %0.2f  /  Right %0.2f" % self.Read()

  def __repr__(self):
    """Representation of (left_float, right_float) photoresistor reading."""
    return repr(self.Read())


class Engine():
  """Car engine (movement) functionality wrapper."""

  _GAIN = 400

  def __init__(self):
    """Create object."""
    self._m = Motor.Motor()

  def Move(self, left_upper, left_lower, right_upper, right_lower, tm):
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
    logging.info('Move %r for %0.2f seconds',
                 (left_upper, left_lower, right_upper, right_lower), tm)
    try:
      self._m.setMotorModel(round(Engine._GAIN * left_upper),
                            round(Engine._GAIN * left_lower),
                            round(Engine._GAIN * right_upper),
                            round(Engine._GAIN * right_lower))
      time.sleep(tm)
    finally:
      self._m.setMotorModel(0, 0, 0, 0)

  def Straight(self, speed, tm):
    """Move car ahead at `speed` for `tm` seconds. Will block."""
    self.Move(speed, speed, speed, speed, tm)

  def Turn(self, angle):
    """Turn car by `angle`. Will block until done.

    Works best when angle is +90.0 or -90.0 as car is actually non-linear.
    """
    logging.info('Turn %0.2f degrees', angle)
    tm = abs(angle * (.7/90))
    if angle > 0:
      self.Move(5, 5, -4, -4, tm)
    else:
      self.Move(-4, -4, 5, 5, tm)


class Noise():
  """Car beeper functionality wrapper. This is a context object."""

  def __init__(self):
    """Create context object."""
    self._b = Buzzer.Buzzer()

  def __enter__(self):
    """Enter context: start making noise."""
    logging.info('Beep!')
    self._b.run('1')
    return self

  def __exit__(self, a, b, c):
    """Leave context: stop making noise."""
    self._b.run('0')
    logging.info('Silence...')


class Light():
  """Car lighting (leds) functionality wrapper. This is a context object."""

  def __init__(self, led_dict):
    """Create context object.

    Args:
      led_dict: like {led_number: (red_uint8, green_uint8, blue_uint8)}
    """
    self._l = Led.Led()
    self._dict = led_dict
    if not self._dict:
      raise Exception('Empty led_dict')

  def __enter__(self):
    """Enter context: turn on the leds."""
    logging.info('Lights @ %r', self._dict)
    for n, (r, g, b) in self._dict.items():
      self._l.ledIndex(1 << n, r, g, b)
    return self

  def __exit__(self, a, b, c):
    """Leave context: turn leds off."""
    self._l.colorWipe(self._l.strip, Led.Color(0, 0, 0))
    logging.info('Lights off')


class Sonar():
  """Car sonar (distance detection) functionality wrapper."""

  def __init__(self):
    """Create object."""
    self._s = Ultrasonic.Ultrasonic()

  def Read(self):
    """Return float distance reading."""
    return self._s.get_distance() / 100.0

  def __str__(self):
    """Print human readable distance reading."""
    return "Distance: %0.3f meters" % self.Read()

  def __repr__(self):
    """Representation of float distance reading."""
    return repr(self.Read())


class Neck():
  """Car neck and head movement functionality wrapper."""

  _NAME = {
      'H': '0',
      'V': '1',
  }

  def __init__(self, offset={'H': 0.0, 'V': 0.0}):
    """Create object.

    Args:
      offset: like {'H': horizontal_offset, 'V': vertical_offset}, in degrees, default is no offset
    """
    self._s = servo.Servo()
    self._o = offset
    if not self._o:
      raise Exception('Empty offset')
    self.Zero()

  def Set(self, servo_dict):
    """Set neck to a position.

    Args:
      servo_dict: like {'H': horizontal_anlge, 'V': vertical_angle}
    """
    logging.info('Neck to position %r', servo_dict)
    for t, a in servo_dict.items():
      t = t.upper()
      if a < -70.0:
        a = -70.0
      if t == 'V' and a < -20.0:
        a = -20.0
      if a > 70.0:
        a = 70.0
      self._s.setServoPwm(Neck._NAME[t], round(a + 90.0 + self._o[t]))

  def Zero(self):
    """Return neck to central position."""
    logging.info('Neck to zero (offset=%r)', self._o)
    self.Set({'H': 0.0, 'V': 0.0})

  def Demo(self):
    """Demos neck movement. Will block."""
    logging.info('Starting neck demo')
    self.Zero()
    try:
      for a in range(-20, 70, 1):
        self.Set({'V': a})
        time.sleep(0.02)
      for a in range(70, -20, -1):
        self.Set({'V': a})
        time.sleep(0.02)
      self.Zero()
      for a in range(-70, 70, 1):
        self.Set({'H': a})
        time.sleep(0.02)
      for a in range(70, -70, -1):
        self.Set({'H': a})
        time.sleep(0.02)
    finally:
      self.Zero()
      logging.info('Neck demo ended')


class Infra():
  """Car lower infra-red sensor functionality wrapper."""

  def __init__(self):
    """Create object."""
    self._l = Line_Tracking.Line_Tracking()

  def Read(self):
    """Return (left_bool, middle_bool, right_bool) infra-red reading."""
    return (Line_Tracking.GPIO.input(self._l.IR01)==True,
            Line_Tracking.GPIO.input(self._l.IR02)==True,
            Line_Tracking.GPIO.input(self._l.IR03)==True)

  def __str__(self):
    """Print human readable infra-red left, middle, and right reading."""
    l, m, r = self.Read()
    return "Infrared: [ %s - %s - %s ]" % (
        'LL' if l else '..', 'MM' if m else '..', 'RR' if r else '..')

  def __repr__(self):
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

  def __init__(self, resolution=_DEFAULT_RESOLUTION, framerate=_DEFAULT_FRAMERATE):
    """Create context object.

    Args:
      resolution: (default 800x600) like (width, height) as ints
      framerate: (default 10) int framerate
    """
    self._c = None
    self._resolution = resolution
    self._framerate = framerate

  def __enter__(self):
    """Enter context: initialize the camera. ATTENTION: will block for 1.5 seconds."""
    self._c = picamera.PiCamera(resolution=self._resolution, framerate=self._framerate)
    logging.info(
        'Starting camera with resolution %r and framerate %d (+wait %0.2fs)',
        self._resolution, self._framerate, Cam._SLEEP_TO_INIT)
    time.sleep(Cam._SLEEP_TO_INIT)
    return self

  def __exit__(self, a, b, c):
    """Leave context: close camera object."""
    if not self._c:
      raise Exception('Not initialized')
    self._c.close()
    logging.info('Camera closed')

  def Click(self):
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

  def Stream(self):
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
      stream.seek(0)  # if we don't rewind again caoture_continuous() will write at the end


def QueueImages(queue, stop_flag):
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
      logging.info('Capture image #%04d', n)
      queue.put((n, img))
  logging.info('Image capture pipeline stopped')
