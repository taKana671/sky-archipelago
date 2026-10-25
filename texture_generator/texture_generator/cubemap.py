import random

import numpy as np

from .cloud import Cloud
from ..utils.color_gradient import SkyColor
from ..utils.noise_process_mixin import NoiseProcessMixin
from ..utils.output_image import make_dir, output


from noise import SimplexNoise
from noise import PerlinNoise
from noise import Fractal3D
from noise import ValueNoise


class CubeMap(NoiseProcessMixin):
    """Create a seamless cubemap noise texture.
       Overlay it onto a background image to output skybox images.
        Args:
            noise_func (callable): method of generating noise.
            size (int): cube size.
    """

    def __init__(self, noise_func, size):
        self.noise = noise_func
        self.size = size
        self.half_size = int(size / 2)
        self.width = size * 6
        self.height = size

    @classmethod
    def from_vfractal(cls, size=256, gain=0.5, lacunarity=2.01, octaves=4):
        value = ValueNoise()
        fract = Fractal3D(value.vnoise3, gain, lacunarity, octaves)
        return cls(fract.fractal, size)

    @classmethod
    def from_sfractal(cls, size=256, gain=0.5, lacunarity=2.01, octaves=4):
        simplex = SimplexNoise()
        fract = Fractal3D(simplex.snoise3, gain, lacunarity, octaves)
        return cls(fract.fractal, size)

    @classmethod
    def from_pfractal(cls, size=256, gain=0.5, lacunarity=2.01, octaves=4):
        perlin = PerlinNoise()
        fract = Fractal3D(perlin.pnoise3, gain, lacunarity, octaves)
        return cls(fract.fractal, size)

    def create_cubemap(self):
        """Generate cubemap like below.

           front   right  back   left   top    bottom
            _________________________________________
           |      |      |      |      |      |      |
           |______|______|______|______|______|______|
        """
        arr = np.zeros((self.height, self.width, 3), np.float32)

        li = random.sample(list('123456789'), 3)
        aa = int(''.join(li))
        bb = int(''.join([li[1], li[2], li[0]]))
        cc = int(''.join(li[::-1]))

        for i in range(self.size * self.size):
            x = i % self.size                           # x position in image
            y = i // self.size                          # y position in image

            a = -self.half_size + x + 0.5               # x position in cube plane; addded 0.5 is to get the center of pixel
            b = -self.half_size + y + 0.5               # y position in cube plane;
            c = -self.half_size                         # z position in cube plane;

            dist_ab = (a ** 2 + b ** 2) ** 0.5
            dist_abc = (dist_ab ** 2 + c ** 2) ** 0.5
            rad = dist_abc * 0.5                        # adjust the distance a bit to get a better radius in the noise field

            a /= rad                                    # normalize the vector
            b /= rad
            c /= rad

            noise_pos = [
                [a, b, c],    # front
                [-c, b, a],   # right
                [-a, b, -c],  # back
                [c, b, -a],   # left
                [a, c, -b],   # top
                [a, -c, b]    # bottom
            ]

            for j in range(6):
                _x = aa + noise_pos[j][0]
                _y = bb + noise_pos[j][1]
                _z = cc + noise_pos[j][2]
                v = self.noise(_x, _y, _z)
                arr[y, x + j * self.size] = v

        arr = np.clip(arr * 255, a_min=0, a_max=255).astype(np.uint8)
        return arr

    def create_skybox_images(self, intensity=1, sky_color=SkyColor.SKYBLUE):
        """Create skybox images.
            Args:
                intensity(int): cloud color intensity; minimum = 1
                sky_color(SkyColor): background color
        """
        img = self.create_cubemap()
        # output(img, 'org')
        img = self.adjust_noise_amount(img)
        # output(img.astype(np.uint8), 'adjust')
        self.generate_images(img, sky_color, intensity)

    def generate_images(self, img, sky_color, intensity):
        parent = make_dir('skybox')
        s_bgr, e_bgr = sky_color.rgb_to_bgr()

        for i in range(6):
            start = self.size * i
            end = start + self.size

            cloud = Cloud(img[:, start: end, :])
            s_color, e_color = s_bgr, e_bgr
            k = None

            match i:
                case 0:
                    stem = 'img_front'   # img_2

                case 1:
                    stem = 'img_right'   # img_0
                    k = 1

                case 2:
                    stem = 'img_back'    # img_3
                    k = 2

                case 3:
                    stem = 'img_left'    # img_1
                    k = 3

                case 4:
                    stem = 'img_top'     # img_4
                    e_color = None

                case 5:
                    stem = 'img_bottom'  # img=5
                    s_color, e_color = e_color, None
                    k = 2

            bg_img = cloud.create_background(s_color, e_color)
            cloud_img = cloud.composite(bg_img, intensity=intensity)

            if k is not None:
                cloud_img = np.rot90(cloud_img, k)

            cloud_img = cloud_img.astype(np.uint8)
            output(cloud_img, stem, parent, with_suffix=False)