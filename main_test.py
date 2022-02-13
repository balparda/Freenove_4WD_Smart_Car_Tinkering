#!/usr/bin/python3 -O
"""Test that the project runs."""

from Code.Server import balparda_follow_the_light
from Code.Server import balparda_lib as lib


lib.StartMultiprocessing()
lib.StartStdErrLogging()


def test_MainPipelines():
  """Test _MainPipelines()."""
  balparda_follow_the_light._MainPipelines(max_runtime=5.0, mock=True)
