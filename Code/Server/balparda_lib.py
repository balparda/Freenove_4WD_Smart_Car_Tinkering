"""Balparda's car API."""

import io
import numpy
import pdb
import time

from PIL import Image

import ADC
import Buzzer
import Led
import Line_Tracking
import Motor
import picamera
import servo
import Ultrasonic


class Battery():

  _BATTERY_FACTOR = 3.0
  _BATTERY_INDEX = 3

  def __init__(self):
    self._a = ADC.Adc()

  def Read(self):
    return Battery._BATTERY_FACTOR * self._a.recvADC(Battery._BATTERY_INDEX)

  def __str__(self):
    return "Battery: %0.2f Volts" % self.Read()

  def __repr__(self):
    return repr(self.Read())


class Photoresistor():

  _PHOTO_INDEX = (0, 1)

  def __init__(self):
    self._a = ADC.Adc()

  def Read(self):
    return (self._a.recvADC(Photoresistor._PHOTO_INDEX[0]), self._a.recvADC(Photoresistor._PHOTO_INDEX[1]))

  def __str__(self):
    return "Photoresistor:  Left %0.2f  /  Right %0.2f" % self.Read()

  def __repr__(self):
    return repr(self.Read())


class Engine():
    
  _GAIN = 400
    
  def __init__(self):
    self._m = Motor.Motor()
    
  def Move(self, a, b, c, d, tm):
    try:
      self._m.setMotorModel(round(Engine._GAIN * a),
                            round(Engine._GAIN * b),
                            round(Engine._GAIN * c),
                            round(Engine._GAIN * d))
      time.sleep(tm)
    finally:
      self._m.setMotorModel(0, 0, 0, 0)

  def Straight(self, speed, tm):
    self.Move(speed, speed, speed, speed, tm)
  
  def Turn(self, angle):
    tm = abs(angle * (.7/90))
    if angle > 0:
      self.Move(5, 5, -4, -4, tm)
    else:
      self.Move(-4, -4, 5, 5, tm)


class Noise():
    
  def __init__(self):
    self._b = Buzzer.Buzzer()
    
  def __enter__(self):
    self._b.run('1')
    return self

  def __exit__(self, a, b, c):
    self._b.run('0')


class Light():
  
  def __init__(self, led_dict):
    self._l = Led.Led()
    self._dict = led_dict
    if not self._dict:
      raise Exception('Empty led_dict')
    
  def __enter__(self):
    for n, (r, g, b) in self._dict.items():
      self._l.ledIndex(1 << n, r, g, b)
    return self

  def __exit__(self, a, b, c):
    self._l.colorWipe(self._l.strip, Led.Color(0, 0, 0))


class Sonar():

  def __init__(self):
    self._s = Ultrasonic.Ultrasonic()

  def Read(self):
    return self._s.get_distance() / 100.0

  def __str__(self):
    return "Distance: %0.3f meters" % self.Read()

  def __repr__(self):
    return repr(self.Read())


class Neck():

  _NAME = {
      'H': '0',
      'V': '1',
  }

  def __init__(self, offset={'H': 0.0, 'V': 0.0}):
    self._s = servo.Servo()
    self._o = offset
    if not self._o:
      raise Exception('Empty offset')

  def Set(self, servo_dict):
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
    self.Set({'H': 0.0, 'V': 0.0})

  def Demo(self):
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


class Infra():

  def __init__(self):
    self._l = Line_Tracking.Line_Tracking()

  def Read(self):
    return (Line_Tracking.GPIO.input(self._l.IR01)==True,
            Line_Tracking.GPIO.input(self._l.IR02)==True,
            Line_Tracking.GPIO.input(self._l.IR03)==True)

  def __str__(self):
    l ,m , r = self.Read()
    return "Infrared: [ %s - %s - %s ]" % ('LL' if l else '..', 'MM' if m else '..', 'RR' if r else '..')

  def __repr__(self):
    return repr(self.Read())


class Cam():

  # this is the size if you ask for a JPG; aspect is 4:3
  _WIDTH = 2592
  _HEIGHT = 1944
  _ASPECT = 4.0 / 3.0
  _DEFAULT_RESOLUTION = (800, 600)
  _DEFAULT_FRAMERATE = 10
  _SLEEP_TO_INIT = 1.5

  def __init__(self, resolution=_DEFAULT_RESOLUTION, framerate=_DEFAULT_FRAMERATE):
    self._c = None
    self._resolution = resolution
    self._framerate = framerate

  def __enter__(self):
    self._c = picamera.PiCamera(resolution=self._resolution, framerate=self._framerate)
    time.sleep(Cam._SLEEP_TO_INIT)
    return self

  def __exit__(self, a, b, c):
    if not self._c:
      raise Exception('Not initialized')
    self._c.close()
    
  def Click(self):
    if not self._c:
      raise Exception('Not initialized')
    stream = io.BytesIO()
    self._c.capture(stream, format='bmp')
    stream.seek(0)
    img = Image.open(stream)
    stream.seek(0)
    return (img, stream.read())
   
  def Greyscale(self):
    img = self.Click()[0]
    pix = numpy.array(img)
    return numpy.round((pix[:,:,0] + pix[:,:,1] + pix[:,:,2]) / 3.0).astype(numpy.uint8)


