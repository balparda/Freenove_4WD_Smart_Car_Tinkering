#!/usr/bin/python3 -O
"""Imaging module."""

import glob
import itertools
import logging
import math
# import pdb
import time

import numpy as np         # type: ignore
from scipy import ndimage  # type: ignore
from matplotlib import pyplot as plt  # type: ignore
from matplotlib import patches
import imageio  # type: ignore

# https://scipy-lectures.org/advanced/image_processing/
# https://docs.scipy.org/doc/
# https://docs.scipy.org/doc/scipy/reference/ndimage.html
# https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.html
# https://imageio.readthedocs.io/en/stable/


def CameraAngleOfView(focal_length, sensor_size):
  """Camera angle of view.

  Args:
    focal_length: Focal lenght, in mm (actually any consistent length unit will work)
    sensor_size: Sensor size, in mm (actually any consistent length unit will work)

  Returns:
    angle of view, in degrees
  """
  return math.degrees(2.0 * math.atan(sensor_size / (2.0 * focal_length)))


class Image():
  """General imaging class."""

  def __init__(self, img):
    """Load an `img` as a copy of another object, as a path, URL, or io.BytesIO.

    Args:
      img: another object, as a path, URL, or io.BytesIO.
    """
    if isinstance(img, np.ndarray):
      self._img = img  # init with data
    else:
      self._img = imageio.imread(img)  # takes file paths, URLs, and io.BytesIO
    self._rgb = len(self._img.shape) == 3

  def Save(self, out):
    """Save image to `out`, which can be a path or an io.BytesIO."""
    imageio.imsave(out, self._img)

  def Show(self, interpolation=True):
    """Show image in pyplot window. Will block.

    Args:
      interpolation: (default True) If True will interpolate pixels.
    """
    # https://matplotlib.org/2.0.2/examples/images_contours_and_fields/interpolation_methods.html
    ipol = 'spline36' if interpolation else 'nearest'
    if self._rgb:
      plt.imshow(self._img, interpolation=ipol)
    else:
      plt.imshow(self._img, cmap=plt.cm.gray, interpolation=ipol)
    plt.show()

  # (R,G,B) multipliers for greyscale conversion
  _GREYSCALE_FACTORS = (299, 587, 114)

  def Grey(self):
    """Return a greyscale image object."""
    # https://stackoverflow.com/questions/12201577/how-can-i-convert-an-rgb-image-into-grayscale-in-python
    if not self._rgb:
      return self._img
    added_img = ((Image._GREYSCALE_FACTORS[0] * self._img[:, :, 0].astype(np.int)) +
                 (Image._GREYSCALE_FACTORS[1] * self._img[:, :, 1].astype(np.int)) +
                 (Image._GREYSCALE_FACTORS[2] * self._img[:, :, 2].astype(np.int)))
    return np.round(added_img / float(sum(Image._GREYSCALE_FACTORS))).astype(np.uint8)

  _BRIGHT_AREAS_BLUR_INDEX = 15.0  # lower value = more bluring

  def _BrightAreas(self):
    """Compute image bright areas.

    Returns:
      (greyscale_img, blurred_img, bright_areas_mask, bright_labels, number_of_labels)
    """
    grey_img = self.Grey() if self._rgb else self._img
    blur_sigma = round(max(self._img.shape) / Image._BRIGHT_AREAS_BLUR_INDEX)
    blur_img = ndimage.gaussian_filter(grey_img, sigma=blur_sigma)
    bright_areas_mask = blur_img > blur_img.mean()
    bright_labels, nlabels = ndimage.label(bright_areas_mask)
    return (grey_img, blur_img, bright_areas_mask, bright_labels, nlabels)

  def BrightnessFocus(self, use_masses=True, plot=False):
    """Get the center of brightness for the image.

    Args:
      use_masses: (default True) If True, counts the pixel values ("mass") summed over the
          brightest image areas; If False, counts each pixel in a bright area with the same
          weight regardless of its actual value.
      plot: (default False) If True will generate a plot for visualization.

    Returns:
      (X,Y) values of the center of brightnes area mass
    """
    grey_img, blur_img, bright_areas_mask, bright_labels, nlabels = self._BrightAreas()
    weight_img = blur_img if use_masses else bright_areas_mask
    label_weights = ndimage.sum(weight_img, labels=bright_labels, index=range(nlabels + 1))
    label_weights[0] = 0  # label 0 does not count here
    com = ndimage.center_of_mass(weight_img, labels=bright_labels, index=np.argmax(label_weights))
    com = (com[1], com[0])  # remember to invert axes
    if plot:
      fig, ax = plt.subplots(2)
      ax[0].imshow(self._img)
      ax[1].imshow(bright_areas_mask.astype(np.uint8) * grey_img, cmap=plt.cm.gray)
      ax[1].add_patch(patches.Circle(com, radius=round(max(self._img.shape) / 100.0), color='red'))
      # ax[1].annotate('x', xy=com, arrowprops={'arrowstyle': '->'})
      plt.show()
    return com

  def PointToAngle(self, x, y, x_angle_view, y_angle_view):
    """Convert image point (x,y) to an angle in the real world based on x/y angle of view.

    Args:
      x: x dimension (int)
      y: y dimension (int)
      x_angle_view: horizontal angle of view (degrees)
      y_angle_view: vertical angle of view (degrees)

    Returns:
      (x_angle, y_angle) the real world angle corresponding to point (x,y) where (0, 0) is the
      center of the image
    """
    y_dim, x_dim = self._img.shape[:2]
    x_px_per_degrees = x_dim / float(x_angle_view)
    y_px_per_degrees = y_dim / float(y_angle_view)
    x -= x_dim / 2
    y -= y_dim / 2
    return (x / x_px_per_degrees, -y / y_px_per_degrees)


def MockQueueImages(queue, stop_flag, mock_images_glob, sleep_time):
  """Define a subprocess for streaming mock images continuously, mocking balparda_lib.QueueImages().

  Expects to be the entry point for a multiprocessing.Process() call. Will write to `queue`
  continuously until `stop_flag` becomes !=0 (True). The written images will be read from
  `mock_images_glob` and retuned in a cycle.

  Args:
    queue: a multiprocessing.Queue object that will receive (n, img) tuples, where n is the
        image counter and img is the Nth imaging.Image object
    stop_flag: a multiprocessing.Value('b', 0, lock=True) byte ('b' signed char) object that
        should start 0 (False) and become 1 (True) when the process should end.
    mock_images_glob: a glob string, like 'path/somefiles*.jpg' for example
    sleep_time: seconds to sleep between images
  """
  time.sleep(sleep_time)
  images = [Image(p) for p in sorted(glob.glob(mock_images_glob))]
  logging.info('Starting image MOCK pipeline with %d images', len(images))
  for n, img in enumerate(itertools.cycle(images)):
    if stop_flag.value:
      break
    logging.debug('Mock image #%04d', n)
    queue.put((n, img))
    time.sleep(sleep_time)
  logging.info('Image MOCK pipeline stopped')
