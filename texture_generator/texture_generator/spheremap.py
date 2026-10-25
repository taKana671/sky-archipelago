import random

import cv2
import numpy as np

from .cloud import Cloud
from noise import Fractal3D
from noise import SimplexNoise
from ..utils.color_gradient import SkyColor
from ..utils.output_image import make_dir, output


class SphereMap:

    def __init__(self, noise_func, size, r):
        self.noise = noise_func
        self.size = size
        self.r = r

    @classmethod
    def from_sfractal(cls, size=256, r=0.1, gain=0.5, lacunarity=2.01, octaves=10):
        simplex = SimplexNoise()
        fract = Fractal3D(simplex.snoise3, gain, lacunarity, octaves)
        return cls(fract.fractal, size, r)

    def create_spheremap(self):
        arr = np.zeros((self.size, self.size, 3), np.float32)

        li = random.sample(list('123456789'), 3)
        aa = int(''.join(li))
        bb = int(''.join([li[1], li[2], li[0]]))
        cc = int(''.join(li[::-1]))

        for j in range(self.size):
            for i in range(self.size):
                x = (i + 0.5) / self.size     # // added half a pixel to get the center of the pixel instead of the top-left
                y = (j + 0.5) / self.size
                rd_x = x * 2 * np.pi
                rd_y = y * np.pi
                y_sin = np.sin(rd_y + np.pi)

                a = aa + self.r * np.sin(rd_x) * y_sin
                b = bb + self.r * np.cos(rd_x) * y_sin
                c = cc + self.r * np.cos(rd_y)
                v = self.noise(a * 10, b * 10, c * 10)
                arr[j, i] = v

        arr = np.clip(arr * 255, a_min=0, a_max=255).astype(np.uint8)
        return arr

    def create_skysphere_image(self):
        img = self.create_spheremap()
        # output(img, 'org')
        cloud = Cloud(img)
        s_bgr, _ = SkyColor.SKYBLUE.rgb_to_bgr()
        bg_img = cloud.create_background(s_bgr, None)
        cloud_img = cloud.composite(bg_img, intensity=1)
        output(cloud_img.astype(np.uint8), 'skysphere')

    def create_cubemap(self):
        img = self.create_spheremap()
        # output(img, 'org')
        img = self.convert_sphere_to_cube(img)
        # output(img, 'converted')
        return img

    def create_skybox_images(self, size=256, intensity=1, sky_color=SkyColor.SKYBLUE):
        img = self.create_cubemap()
        # output(img, 'skybox')
        self.generate_images(img, intensity, sky_color)

    def rotate(self, x, y, z, roll, pitch, heading):
        roll = roll * np.pi / 180
        pitch = pitch * np.pi / 180
        heading = heading * np.pi / 180

        mat_r = np.array([
            [1, 0, 0],
            [0, np.cos(roll), np.sin(roll)],
            [0, -np.sin(roll), np.cos(roll)]
        ])

        mat_p = np.array([
            [np.cos(pitch), 0, -np.sin(pitch)],
            [0, 1, 0],
            [np.sin(pitch), 0, np.cos(pitch)]
        ])

        mat_h = np.array([
            [np.cos(heading), np.sin(heading), 0],
            [-np.sin(heading), np.cos(heading), 0],
            [0, 0, 1]
        ])

        mat = np.dot(mat_h, np.dot(mat_p, mat_r))
        xd = mat[0][0] * x + mat[0][1] * y + mat[0][2] * z
        yd = mat[1][0] * x + mat[1][1] * y + mat[1][2] * z
        zd = mat[2][0] * x + mat[2][1] * y + mat[2][2] * z

        return xd, yd, zd

    def create_coords_group(self, img_w):
        base_w = 0.5
        w = np.linspace(-base_w, base_w, img_w, endpoint=False)
        h = np.linspace(-base_w, base_w, img_w, endpoint=False)

        w = w + base_w / img_w
        h = h + base_w / img_w
        ww, hh = np.meshgrid(w, h)

        a1 = 2 * ww
        a2 = 2 * hh
        x = (1 / (1 + a1 ** 2 + a2 ** 2)) ** 0.5
        y = a1 * x
        z = a2 * x

        return x, y, z

    def convert_equirectangular(self, x, y, z):
        # Convert to latitude and longitude.
        phi = np.arcsin(z)
        theta = np.arcsin(np.clip(y / np.cos(phi), -1, 1))
        theta = np.where((x < 0) & (y < 0), -np.pi - theta, theta)
        theta = np.where((x < 0) & (y > 0), np.pi - theta, theta)

        return phi, theta

    def remap_equirectangular(self, img, phi, theta):
        h, w = img.shape[:2]
        # Normalize to image coordinates.
        phi = (phi * h / np.pi + h / 2).astype(np.float32) - 0.5
        theta = (theta * w / (2 * np.pi) + w / 2).astype(np.float32) - 0.5

        return cv2.remap(img, theta, phi, cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)

    def convert_sphere_to_cube(self, spheremap):
        x, y, z = self.create_coords_group(self.size)

        phi, theta = self.convert_equirectangular(x, y, z)
        front = self.remap_equirectangular(spheremap, phi, theta)

        rx, ry, rz = self.rotate(x, y, z, 0, 0, -90)
        phi, theta = self.convert_equirectangular(rx, ry, rz)
        right = self.remap_equirectangular(spheremap, phi, theta)

        rx, ry, rz = self.rotate(x, y, z, 0, 0, 90)
        phi, theta = self.convert_equirectangular(rx, ry, rz)
        left = self.remap_equirectangular(spheremap, phi, theta)

        rx, ry, rz = self.rotate(x, y, z, 0, 0, 180)
        phi, theta = self.convert_equirectangular(rx, ry, rz)
        back = self.remap_equirectangular(spheremap, phi, theta)

        rx, ry, rz = self.rotate(x, y, z, 0, 90, 0)
        phi, theta = self.convert_equirectangular(rx, ry, rz)
        bottom = self.remap_equirectangular(spheremap, phi, theta)

        rx, ry, rz = self.rotate(x, y, z, 0, -90, 0)
        phi, theta = self.convert_equirectangular(rx, ry, rz)
        up = self.remap_equirectangular(spheremap, phi, theta)

        img = np.zeros((self.size * 3, self.size * 4, 3), dtype=spheremap.dtype)

        img[self.size * 1:self.size * 2, :self.size * 1] = left
        img[self.size * 1:self.size * 2, self.size * 1:self.size * 2] = front
        img[self.size * 1:self.size * 2, self.size * 2:self.size * 3] = right
        img[self.size * 1:self.size * 2, self.size * 3:] = back
        img[:self.size * 1, self.size * 1:self.size * 2] = up
        img[self.size * 2:, self.size * 1:self.size * 2] = bottom

        return img

    def generate_images(self, img, intensity, sky_color):
        parent = make_dir('skybox')
        s_bgr, _ = sky_color.rgb_to_bgr()

        h, _ = img.shape[:2]
        size = int(h / 3)

        for j in range(3):
            for i in range(4):
                k = None

                match (j, i):
                    case (0, 1):
                        stem = 'img_top'     # img_4
                        arr = img[:size, size: size * 2, :]

                    case (2, 1):
                        stem = 'img_bottom'  # img_5
                        arr = img[size * j:, size: size * 2, :]
                        k = 2

                    case (1, 0):
                        stem = 'img_left'    # img_1
                        arr = img[size: size * 2, :size, :]
                        k = 3

                    case (1, 1):
                        stem = 'img_front'   # img_2
                        arr = img[size: size * 2, size * i: size * (i + 1), :]

                    case (1, 2):
                        stem = 'img_right'   # img_0
                        arr = img[size: size * 2, size * i: size * (i + 1), :]
                        k = 1

                    case (1, 3):
                        stem = 'img_back'    # img_3
                        arr = img[size: size * 2, size * i: size * (i + 1), :]
                        k = 2

                    case _:
                        continue

                cloud = Cloud(arr)
                bg_img = cloud.create_background(s_bgr, None)
                cloud_img = cloud.composite(bg_img, intensity=intensity)

                if k is not None:
                    cloud_img = np.rot90(cloud_img, k)

                output(cloud_img.astype(np.uint8), stem, parent, with_suffix=False)