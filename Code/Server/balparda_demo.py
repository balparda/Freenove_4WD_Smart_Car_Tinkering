#!/usr/bin/python3 -O
"""Testing (scratchpad) and child-friendly module."""

# import pdb

from Code.Server import balparda_car as car
from Code.Server import luna_lib as ll

bt = car.Battery()
ph = car.Photoresistor()
sn = car.Sonar()
ir = car.Infra()

print(bt)
print(ph)
print(sn)
print(ir)

with ll.BB(), car.Neck(offset=(6, -30)) as nk:

  nk.Zero()
  ll.Pa()
  nk.Zero()
  ll.Pa()

  raise

  ll.Fr()

  ll.Es()

  ll.Di()

  ll.Pa()

  ll.Tr()
