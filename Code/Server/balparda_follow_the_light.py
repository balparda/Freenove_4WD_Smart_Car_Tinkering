#!/usr/bin/python3 -O
"""Follow-the-Light automaton program for the car."""

_MOCK = True

import logging
import multiprocessing
import pdb
import sys
import time

from scipy import misc

import balparda_imaging as imaging
import balparda_lib as lib
if not _MOCK:
  import balparda_car as car
else:
  car = None


_N_IMAGES_TO_TIME = 30


@lib.Timed
def DirectCapture():
  """Time direct capture and processing."""
  with lib.Cam() as cam:
    for n, (img, _) in enumerate(cam.Stream()):
      com = img.BrightnessFocus()
      logging.info('%0.2f : %r', time.time(), com)
      if n >= (_N_IMAGES_TO_TIME - 1):
        break


@lib.Timed
def ImageQueue():
  """Time one process capturing images."""
  img_queue = multiprocessing.Queue()
  img_stop = multiprocessing.Value('b', 0, lock=True)
  img_process = multiprocessing.Process(target=car.QueueImages, args=(img_queue, img_stop))
  img_process.start()
  try:
    for _ in range(_N_IMAGES_TO_TIME):
      img = img_queue.get()
      com = img.BrightnessFocus()
      logging.info('%0.2f : %r', time.time(), com)
  finally:
    img_stop.value = 1
    img_process.join()


@lib.Timed
def ImageAndProcessingQueue(mock=False):
  """Time separate imaging and process processes."""
  # create queues and semaphores
  img_queue = multiprocessing.JoinableQueue()
  img_stop = multiprocessing.Value('b', 0, lock=True)
  brightness_queue = multiprocessing.JoinableQueue()
  brightness_stop = multiprocessing.Value('b', 0, lock=True)
  # setup image process (real or mock)
  img_process = multiprocessing.Process(
      target=imaging.MockQueueImages if mock else car.QueueImages,
      name='image-pipeline',
      args=(img_queue, img_stop, 'testimg/capture-001-*.jpg', .7) if mock else (img_queue, img_stop),
      daemon=True)
  # setup processing pipeline (feeding real or mock images)
  brightness_process = multiprocessing.Process(
      target=lib.UpToDateProcessingPipeline,
      name='processing-pipeline',
      args=(img_queue,
            brightness_queue,
            lambda i: (i[0], i[1], i[1].BrightnessFocus()),
            brightness_stop),
      daemon=True)
  # start
  logging.info('Starting pipeline processes')
  img_process.start()
  brightness_process.start()
  try:
    # process the items
    for n in range(_N_IMAGES_TO_TIME):
      n_img, img, focus = brightness_queue.get()
      try:
        logging.info('Got image+focus %d (#%04d) ==>> focus is %r', n, n_img, focus)
      finally:
        brightness_queue.task_done()
  finally:
    # signal stop and wait for queues
    img_stop.value = 1
    brightness_stop.value = 1
    logging.info('Waiting for image pipeline')
    img_process.join()
    logging.info('Waiting for processing pipeline')
    brightness_process.join()
    # we need to finish consuming brightness_queue now
    if brightness_queue.qsize():
      logging.info('Discarding %d remaining incoming image foci', brightness_queue.qsize())
    while brightness_queue.qsize():
      brightness_queue.get()  # discard value
      brightness_queue.task_done()


def main():
  """Execute main method."""
  logging.info('Start')
  #DirectCapture()
  #ImageQueue()
  ImageAndProcessingQueue(mock=_MOCK)
  logging.info('End')
  return

  args = sys.argv[1:]
  if args:
    img = Image(args[-1])
  else:
    img = Image(misc.face())
  com = img.BrightnessFocus(plot=True)
  logging.info(repr(com))
  # plt.imshow(img._img, cmap=plt.cm.gray)
  # plt.annotate('x', xy=com, arrowprops={'arrowstyle': '->'})
  # plt.add_patch(patches.Circle(com, radius=round(max(self._img.shape) / 50.0), color='red'))
  # plt.show()
  # img.Show()


if __name__ == '__main__':
  lib.StartMultiprocessing()
  lib.StartStdErrLogging()
  main()
