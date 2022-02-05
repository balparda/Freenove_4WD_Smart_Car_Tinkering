#!/usr/bin/python3 -O
"""Testing (scratchpad) and child-friendly module."""

import pdb
import time

import balparda_lib as lib
from luna_lib import *

bt = lib.Battery()
ph = lib.Photoresistor()
sn = lib.Sonar()
nk = lib.Neck(offset={'H': 6.0, 'V': -23.0})
ir = lib.Infra()

print(bt)
print(ph)
print(sn)
print(ir)

with lib.Cam() as cam:#, BB():

  pdb.set_trace()
  img = cam.Greyscale()
  # continue: https://scipy-lectures.org/advanced/image_processing/


  #nk.Demo()

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
