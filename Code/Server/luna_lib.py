#!/usr/bin/python3 -O
"""Module will simplify car concepts to its bare minimal call, for beginner understanding."""

import time
import balparda_car as car


_ENG = car.Engine()


class BB():  # bi-bi, barulho, luz
  """Class "bi-bi": Noise and light."""

  def __init__(self):
    """Create object."""
    self._n = car.Noise()
    self._l = car.Light({n: (255, 0, 255) for n in range(8)})

  def __enter__(self):
    """Start noise and light."""
    self._n.__enter__()
    self._l.__enter__()

  def __exit__(self, a, b, c):
    """End noise and light."""
    self._n.__exit__(a, b, c)
    self._l.__exit__(a, b, c)


def Fr():
  """FRente: Forward."""
  _ENG.Straight(1.5, 1.5)


def Tr():
  """TRás: Para Trás."""
  _ENG.Straight(-1.5, 1.5)


def Di():
  """DIreita."""
  _ENG.Turn(90)


def Es():
  """ESquerda."""
  _ENG.Turn(-90)


def Pa():
  """Pausa (de 1.5 segundos)."""
  time.sleep(1.5)
