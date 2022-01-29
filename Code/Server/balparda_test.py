import time
import ADC
import balparda_lib as lib
from luna_lib import *

adc = ADC.Adc()
print("Photoresistor:  Left %f  /  Right %f" % (adc.recvADC(0), adc.recvADC(1)))
print("Battery: %r" % (3.0*adc.recvADC(3)))

with BB():

  Fr()
    
  Es()
    
  Di()
    
  Pa()
    
  Tr()

