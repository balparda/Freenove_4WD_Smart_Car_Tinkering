import time
import balparda_lib as lib


_ENG = lib.Engine()


class BB():  # bi-bi, barulho, luz

  def __init__(self):
    self._n = lib.Noise()
    self._l = lib.Light({n: (255, 0, 255) for n in range(8)})

  def __enter__(self):
    self._n.__enter__()
    self._l.__enter__()

  def __exit__(self, a, b, c):
    self._n.__exit__(a, b, c)
    self._l.__exit__(a, b, c)


def Fr():  # frente
  _ENG.Straight(2, 1.5)

  
def Tr():  # tras
  _ENG.Straight(-2, 1.5)

  
def Di():  # direita
  _ENG.Turn(90)

  
def Es():  # esquerda
  _ENG.Turn(-90)

  
def Pa():  # pausa
  time.sleep(1.5)
