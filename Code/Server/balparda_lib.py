import time
import Motor
#import ADC
import Buzzer
import Led


class Engine():
    
  def __init__(self):
    self._m = Motor.Motor()
    
  def Move(self, a, b, c, d, tm):
    try:
      self._m.setMotorModel(400*a, 400*b, 400*c, 400*d)
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


class Led():
  pass

