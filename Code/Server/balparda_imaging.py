#!/usr/bin/python3 -O
"""Imaging module."""

import pdb
import sys

# https://scipy-lectures.org/advanced/image_processing/
import numpy as np
#import scipy  # https://docs.scipy.org/doc/
from scipy import misc
from scipy import ndimage  # https://docs.scipy.org/doc/scipy/reference/ndimage.html
                           # https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.html
from matplotlib import pyplot as plt
from matplotlib import patches
import imageio  # https://imageio.readthedocs.io/en/stable/


class Image():

  def __init__(self, img):
    if isinstance(img, np.ndarray):
      self._img = img  # init with data
    else:
      self._img = imageio.imread(img)  # takes file paths, URLs, and io.BytesIO
    self._rgb = len(self._img.shape) == 3

  def Save(self, out):
    imageio.imsave(out, self._img)

  def Show(self, interpolation=True):
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
    # https://stackoverflow.com/questions/12201577/how-can-i-convert-an-rgb-image-into-grayscale-in-python
    if not self._rgb:
      return self._img
    added_img = ((Image._GREYSCALE_FACTORS[0] * self._img[:, :, 0].astype('int'))
                 + (Image._GREYSCALE_FACTORS[1]
                    * self._img[:, :, 1].astype('int'))
                 + (Image._GREYSCALE_FACTORS[2] * self._img[:, :, 2].astype('int')))
    return np.round(added_img / float(sum(Image._GREYSCALE_FACTORS))).astype('uint8')

  _BRIGHT_AREAS_BLUR_INDEX = 15.0  # lower value = more bluring

  def _BrightAreas(self):
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
    label_weights = ndimage.sum_labels(
      weight_img, labels=bright_labels, index=range(nlabels + 1))
    label_weights[0] = 0  # label 0 does not count here
    com = ndimage.center_of_mass(
      weight_img, labels=bright_labels, index=np.argmax(label_weights))
    com = (com[1], com[0])  # remember to invert axes
    if plot:
      fig, ax = plt.subplots(2)
      ax[0].imshow(self._img)
      ax[1].imshow(bright_areas_mask.astype(
        np.uint8) * grey_img, cmap=plt.cm.gray)
      ax[1].add_patch(patches.Circle(com, radius=round(
        max(self._img.shape) / 100.0), color='red'))
      plt.show()
    return com


def main():
  args = sys.argv[1:]
  if args:
    img = Image(args[-1])
  else:
    img = Image(misc.face())
  com = img.BrightnessFocus(plot=True)
  print(com)


main()


#plt.imshow(img._img, cmap=plt.cm.gray)
#plt.annotate('x', xy=com, arrowprops={'arrowstyle': '->'})
#plt.add_patch(patches.Circle(com, radius=round(max(self._img.shape) / 50.0), color='red'))
#plt.show()

#img.Show()
