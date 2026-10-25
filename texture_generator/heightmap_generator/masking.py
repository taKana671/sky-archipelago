import numpy as np
import cv2

from noise import SimplexNoise, PerlinNoise
from utils import output_image


class Masking:

    @staticmethod
    def composite(noise, mask, white_areas=True):
        """masking
            Args:
                noise (str | Numpy.ndarray):
                    Noise is assumed to be generated using methods within the “noise” directory.
                    Specify either the file path of the noise image or a Numpy.ndarray.
                    When specifying a Numpy.ndarray, elements must be in the range 0.0 to 1.0.
                mask (str | Numpy.ndarray):
                    Specify either the file path of the mask image or a Numpy.ndarray.
                    When specifying a Numpy.ndarray, elements must be in the range 0 to 255.
                white_areas (bool):
                    When True is specified, the white areas of the mask image are displayed and
                    the black areas are hidden. When False is specified, the black areas are displayed and
                    the white areas are hidden. The default is True.
        """
        if isinstance(mask, str):
            mask = cv2.imread(mask)

        if mask.ndim == 2:
            mask = mask.reshape(*mask.shape, 1)

        if isinstance(noise, str):
            noise = cv2.imread(noise)
            noise = noise / 255

        if noise.ndim == 2:
            noise = np.stack([noise] * 3, axis=-1)

        if white_areas:
            img = noise * (mask / 255)
        else:
            img = noise * (1 - mask / 255)

        return img

    @staticmethod
    def fractal_simplex_noise(mask, size=256, t=None, gain=0.5, lacunarity=2.01, octaves=4,
                              parent='.', with_suffix=True):
        simplex = SimplexNoise()
        noise_img = simplex.fractal2(size, size, t, gain, lacunarity, octaves)
        # noise_img = np.stack([noise_img] * 3, axis=-1)

        img = Masking.composite(noise_img, mask)
        img = np.clip(img * 255, a_min=0, a_max=255).astype(np.uint8)
        output_image.output(img, 'masked_image', parent, with_suffix)

    @staticmethod
    def fractal_perlin_noise(mask, size=256, grid=4, t=None, gain=0.5, lacunarity=2.01, octaves=4,
                             parent='.', with_suffix=True):
        perlin = PerlinNoise()
        noise_img = perlin.fractal2(size, grid, t, gain, lacunarity, octaves)
        # noise_img = np.stack([noise_img] * 3, axis=-1)

        img = Masking.composite(noise_img, mask)
        img = np.clip(img * 255, a_min=0, a_max=255).astype(np.uint8)
        output_image.output(img, 'masked_image', parent, with_suffix)
