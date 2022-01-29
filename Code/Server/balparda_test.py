import time
#import Motor
import ADC
#import Buzzer
import Led
import balparda_lib as lib

adc = ADC.Adc()
print("Photoresistor:  Left %f  /  Right %f" % (adc.recvADC(0), adc.recvADC(1)))
print("Battery: %r" % (3.0*adc.recvADC(3)))

led = Led.Led()

eng = lib.Engine()

def Fr():
  eng.Straight(1, 1.5)
  
def Tr():
  eng.Straight(-1, 1.5)
  
def Di():
  eng.Turn(90)
  
def Es():
  eng.Turn(-90)
  
def Pa():
  time.sleep(1.5)

led.ledIndex(1, 255, 255, 255)
led.ledIndex(2, 255, 255, 255)
led.ledIndex(4, 255, 255, 255)
led.ledIndex(8, 255, 255, 255)
led.ledIndex(16, 255, 255, 255)
led.ledIndex(32, 255, 255, 255)
led.ledIndex(64, 255, 255, 255)
led.ledIndex(128, 255, 255, 255)
try:
  with lib.Noise():

    Fr()
  
    Di()
  
    Pa()
  
    Es()
  
    Tr()
  
    Di()
  
    Fr()

finally:
  led.colorWipe(led.strip, Led.Color(0, 0, 0))

