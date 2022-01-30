import time
import balparda_lib as lib
from luna_lib import *

bt = lib.Battery()
ph = lib.Photoresistor()
sn = lib.Sonar()
nk = lib.Neck(offset={'H': 6.0, 'V': -23.0})

print(bt)
print(ph)
print(sn)

with BB():

  nk.Demo()

  raise

  nk.Set({'H': 0, 'V': 0})
  Pa()
  nk.Zero()
  Pa()

  raise

  Fr()
    
  Es()
    
  Di()
    
  Pa()
    
  Tr()

