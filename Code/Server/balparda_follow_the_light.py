#!/usr/bin/python3 -O
"""Follow-the-Light automaton program for the car."""

# import pdb
import sys
import time

from scipy import misc

import balparda_lib as lib


def main():
  """Execute main method."""
  # pdb.set_trace()
  with lib.Cam() as cam:
    for img in cam.Stream():
      print(time.time())

  break

  args = sys.argv[1:]
  if args:
    img = Image(args[-1])
  else:
    img = Image(misc.face())
  com = img.BrightnessFocus(plot=True)
  print(com)
  # plt.imshow(img._img, cmap=plt.cm.gray)
  # plt.annotate('x', xy=com, arrowprops={'arrowstyle': '->'})
  # plt.add_patch(patches.Circle(com, radius=round(max(self._img.shape) / 50.0), color='red'))
  # plt.show()
  # img.Show()


main()
