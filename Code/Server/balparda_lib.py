import time
import ADC
import Motor
import Buzzer
import Led


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
      self._m.setMotorModel(Engine._GAIN * a,
                            Engine._GAIN * b,
                            Engine._GAIN * c,
                            Engine._GAIN * d)
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

  def __exit__(self, a, b, c):
    self._l.colorWipe(self._l.strip, Led.Color(0, 0, 0))

