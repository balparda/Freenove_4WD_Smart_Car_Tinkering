#!/usr/bin/python3 -O
"""Capture images for testing and offline streaming."""

import pdb

import balparda_lib as lib


_TEMPLATE = 'testimg/capture-001-%03d.jpg'


def main():
  """Execute main method."""
  with lib.Cam() as cam:
    #pdb.set_trace()
    for n, (img, _) in enumerate(cam.Stream()):
      path = _TEMPLATE % n
      img.Save(path)
      print('Saved: %r' % path)


if __name__ == '__main__':
  main()
