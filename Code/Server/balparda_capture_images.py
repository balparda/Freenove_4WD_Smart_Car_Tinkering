#!/usr/bin/python3 -O
"""Capture images for testing and offline streaming."""

# import pdb

from Code.Server import balparda_car as car

_TEMPLATE = 'testimg/capture-001-%03d.jpg'


def main() -> None:
  """Execute main method."""
  with car.Cam() as cam:
    for n, (img, _) in enumerate(cam.Stream()):
      path = _TEMPLATE % n
      img.Save(path)
      print('Saved: %r' % path)


if __name__ == '__main__':
  main()
