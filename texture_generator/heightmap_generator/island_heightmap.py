import numpy as np
import random

from noise import PerlinNoise, SimplexNoise, Fractal2D
from ..mask.radial_gradient_generator import RadialGradientMask
from ..utils import output_image


class IslandHeightmap:
    """A class to generate an island heightmap.
        Args:
            noise (function):
            size (int): The size of an image.
            island_center_h (int): y-axis center of an island; must be positive; size // 2, if not specified.
            island_center_w (int): x-axis center of an island; must be positive; size // 2, if not specified.
            island_size (float): The larger the island_size, the smaller the island become.
            reverse (bool): If False, basin-shaped heightmap is generated.
    """

    def __init__(self, noise, size=256, island_center_h=None,
                 island_center_w=None, island_size=2, reverse=False):
        self.noise = noise
        self.size = size
        inner_to_outer = not reverse
        self.mask = RadialGradientMask(
            size, size, island_center_h, island_center_w, island_size, inner_to_outer
        )

    @classmethod
    def from_sfractal(cls, size=256, gain=0.5, lacunarity=2.01, octaves=4,
                      island_center_h=None, island_center_w=None, island_size=2, reverse=False):
        simplex = SimplexNoise()
        noise = Fractal2D(simplex.snoise2, gain, lacunarity, octaves)

        return cls(noise.fractal, size, island_center_h, island_center_w, island_size, reverse)

    @classmethod
    def from_pfractal(cls, size=256, gain=0.5, lacunarity=2.01, octaves=4,
                      island_center_h=None, island_center_w=None, island_size=2, reverse=False):
        perlin = PerlinNoise()
        noise = Fractal2D(perlin.pnoise2, gain, lacunarity, octaves)

        return cls(noise.fractal, size, island_center_h, island_center_w, island_size, reverse)

    def get_height(self, x, y, t):
        noise_v = self.noise(x / self.size + t, y / self.size + t)
        mask_v = self.mask.get_gradient(x, y)[0]
        v = 0 if mask_v >= noise_v else noise_v - mask_v
        return v

    def create_island_heightmap(self, island_center_h=None, island_center_w=None, island_size=None,
                                t=None, parent='.', with_suffix=True, bit8=True):
        if t is None:
            t = random.uniform(0, 1000)

        if island_center_h is not None:
            self.mask.center_h = island_center_h

        if island_center_w is not None:
            self.mask.center_w = island_center_w

        if island_size is not None:
            self.mask.gradient_size = island_size

        arr = np.array(
            [self.get_height(x, y, t)
                for y in range(self.size) for x in range(self.size)]
        )

        arr = arr.reshape(self.size, self.size)

        if bit8:
            arr = np.clip(arr * 255, a_min=0, a_max=255).astype(np.uint8)
            prefix = '8bit'
        else:
            arr = np.clip(arr * 65535, a_min=0, a_max=65535).astype(np.uint16)
            prefix = '16bit'

        output_image.output(arr, f'{prefix}_island_heightmap', parent, with_suffix)
