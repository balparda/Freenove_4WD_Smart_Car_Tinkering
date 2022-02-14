#!/usr/bin/python3 -O
"""Follow-the-Light automaton program for the car."""

# import pdb  # noqa: E402

from Code.Server import balparda_follow_the_light
from Code.Server import balparda_lib as lib


if __name__ == '__main__':
  lib.StartMultiprocessing()
  lib.StartStdErrLogging()
  balparda_follow_the_light.main()
