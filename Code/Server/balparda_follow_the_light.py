#!/usr/bin/python3 -O
"""Follow-the-Light automaton program for the car."""

import multiprocessing
import pdb
import sys
import time

from scipy import misc

import balparda_imaging as imaging
import balparda_lib as lib


_N_IMAGES_TO_TIME = 3


@lib.Timed
def DirectCapture():
  """Time direct capture and processing."""
  with lib.Cam() as cam:
    for n, (img, _) in enumerate(cam.Stream()):
      com = img.BrightnessFocus()
      print('%0.2f : %r' % (time.time(), com))
      if n >= (_N_IMAGES_TO_TIME - 1):
        break


@lib.Timed
def ImageQueue():
  """Time one process capturing images."""
  img_queue = multiprocessing.Queue()
  img_stop = multiprocessing.Value('b', 0, lock=True)
  img_process = multiprocessing.Process(target=lib.QueueImages, args=(img_queue, img_stop))
  img_process.start()
  try:
    for _ in range(_N_IMAGES_TO_TIME):
      img = img_queue.get()
      com = img.BrightnessFocus()
      print('%0.2f : %r' % (time.time(), com))
  finally:
    img_stop.value = 1
    img_process.join()


@lib.Timed
def ImageAndProcessingQueue():
  """Time separate imaging and process processes."""
  img_queue = multiprocessing.Queue()
  img_stop = multiprocessing.Value('b', 0, lock=True)
  img_process = multiprocessing.Process(
      target=lib.QueueImages,
      name='image-generator',
      args=(img_queue, img_stop),
      daemon=True)
  brightness_queue = multiprocessing.Queue()
  brightness_stop = multiprocessing.Value('b', 0, lock=True)
  brightness_process = multiprocessing.Process(
      target=imaging.ProcessingPipeline,
      name='image-processing',
      args=(img_queue,
            brightness_queue,
            lambda i: (i[0], i[1], i[1].BrightnessFocus()),
            brightness_stop),
      daemon=True)
  img_process.start()
  brightness_process.start()
  try:
    for n in range(_N_IMAGES_TO_TIME):
      print('MAIN: GET %d' % n)
      n_img, img, focus = brightness_queue.get()
      print('%d - %d - %0.2f : %r' % (n, n_img, time.time(), focus))
  finally:
    img_stop.value = 1
    brightness_stop.value = 1
    print('MAIN: PP JOIN')
    brightness_process.join()
    print('MAIN: IMG JOIN')
    img_process.join()


def main():
  """Execute main method."""
  #DirectCapture()
  #ImageQueue()
  ImageAndProcessingQueue()
  return

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


if __name__ == '__main__':
  multiprocessing.set_start_method('fork')
  main()
