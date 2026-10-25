import copy

import cv2
import numpy as np

from texture_generator.utils.noise_process_mixin import NoiseProcessMixin
from ..utils.output_image import output
from ..utils.color_gradient import SkyColor  # get_gradient_3d
from ..mask.linear_gradient_generator import LinearGradient

from noise import ValueNoise
from noise import PerlinNoise
from noise import SimplexNoise


class Cloud(NoiseProcessMixin):
    """Create a mask image from noise and overlay it
       onto a background image to generate a cloud image.
        Args:
            arr (numpy.ndarray): 3-dimensional
    """

    def __init__(self, arr):
        self._arr = arr
        self.img = copy.deepcopy(arr)
        self.height, self.width = arr.shape[:2]

    def _convert(self, arr):
        arr = np.clip(arr * 255, a_min=0, a_max=255).astype(np.uint8)
        arr = np.stack([arr] * 3, axis=2)
        return arr

    @classmethod
    def from_file(cls, file_path):
        arr = cv2.imread(file_path)
        return cls(arr)

    @classmethod
    def from_vfractal(cls, size=256, grid=4, t=None, gain=0.5, lacunarity=2.01, octaves=4):
        vnoise = ValueNoise()
        arr = vnoise.fractal2(size, grid, t, gain, lacunarity, octaves)
        arr = cls._convert(cls, arr)
        return cls(arr)

    @classmethod
    def from_pfractal(cls, size=256, grid=4, t=None, gain=0.5, lacunarity=2.01, octaves=4):
        pnoise = PerlinNoise()
        arr = pnoise.fractal2(size, grid, t, gain, lacunarity, octaves)
        arr = cls._convert(cls, arr)
        return cls(arr)

    @classmethod
    def from_sfractal(cls, width=256, height=256, t=None,
                      gain=0.5, lacunarity=2.01, octaves=4):
        snoise = SimplexNoise()
        arr = snoise.fractal2(width, height, t, gain, lacunarity, octaves)
        arr = cls._convert(cls, arr)
        return cls(arr)

    def create_cloud_image(self, intensity=1, sky_color=SkyColor.SKYBLUE, bbox=None):
        """Output a cloud image.
            Args:
                intensity(int): cloud color intensity; minimum = 1
                sky_color(SkyColor): background color
                bbox(list): 4 points of a rectangle in the noise image;
                            must be the format of [[int, int], [int, int], [int, int], [int, int]].
        """
        self.create_cloud_cover(bbox)
        bg_img = self.create_background(*sky_color.rgb_to_bgr())
        cloud_img = self.composite(bg_img, intensity)
        cloud_img = cloud_img.astype(np.uint8)
        output(cloud_img, 'cloud')

    def create_cloud_cover(self, bbox):
        # output(self.img.astype(np.uint8), 'org')
        self.img = self.adjust_noise_amount(self._arr)
        # output(self.img.astype(np.uint8), 'adjust')
        src_pts = self.define_src_pts(bbox)
        self.img = self.perspective_transform(src_pts)
        # output(self.img.astype(np.uint8), 'pers')

    def define_src_pts(self, bbox):
        w = self.width - 1
        h = self.height - 1

        if bbox is None:
            pt_a = [w * 0.392, 0]
            pt_b = [w * 0.039, h]
            pt_c = [w * 0.96, h]
            pt_d = [w * 0.784, 0]
            return self.round_arr([pt_a, pt_b, pt_c, pt_d])

        if len(bbox) != 4:
            raise ValueError(f'bbox must have 4 elements. got={len(bbox)}.')

        for pt in bbox:
            if len(pt) != 2:
                raise ValueError(f'The length of each element of bbox must be 2. got={pt}.')

        return [[min(max(0, pt[0]), w), min(max(0, pt[1]), h)] for pt in bbox]

    def perspective_transform(self, src_pts):
        """Perspective transformation
            Args:
                src_pts (numpy.ndarray or list): 4 points of a rectangle in the noise image;
                            must be [[ax, ay], [bx, by], [cx, cy], [dx, dy]].
                            self.img              transformed
                           ________________     a ________________d
                          |     d_____ c   |     |                |
                          |     /    /     |     |                |
                          |    /____/      | --> |                |
                          |   a     b      |     |                |
                          |________________|    b|________________|c
        """
        src_pts = np.array(src_pts, np.float32)
        # src_pts = np.array([[100, 0], [10, 255], [245, 255], [200, 0]], np.float32)

        w, h = self.width - 1, self.height - 1
        dst_pts = np.array([[0, 0], [0, h], [w, h], [w, 0]], np.float32)
        mat = cv2.getPerspectiveTransform(src_pts, dst_pts)
        pers_img = cv2.warpPerspective(self.img, mat, (self.width, self.height), flags=cv2.INTER_LINEAR)

        pers_img = pers_img - pers_img.min()
        pers_img = self.round_arr(pers_img / pers_img.max() * 255)

        return pers_img

    def create_background(self, start_color, end_color=None):
        if end_color is None:
            bg_img = np.full((self.height, self.width, 3), start_color, np.uint8)
        else:
            vertical_grad = LinearGradient(
                self.height, self.width, start_color, end_color, (False, False, False))
            bg_img = vertical_grad.get_gradient_3d()

        return bg_img

    def composite(self, bg_img, intensity=1):
        """Alpha blending
            Args:
                bg_image (numpy.ndarray): 3-dimensional
                intensity (int): cloud color intensity
        """
        wh_img = np.full((self.height, self.width, 3), [255, 255, 255], np.uint8)

        for _ in range(intensity):
            bg_img = bg_img * (1 - self.img / 255) + wh_img * (self.img / 255)

        return bg_img