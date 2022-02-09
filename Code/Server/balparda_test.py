#!/usr/bin/python3 -O
"""Testing (scratchpad) and child-friendly module."""

import pdb
import time

import balparda_car as car
from luna_lib import *

bt = car.Battery()
ph = car.Photoresistor()
sn = car.Sonar()
nk = car.Neck(offset={'H': 6.0, 'V': -23.0})
ir = car.Infra()

print(bt)
print(ph)
print(sn)
print(ir)

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
