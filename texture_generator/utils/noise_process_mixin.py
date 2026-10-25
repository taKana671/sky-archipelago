import math

import numpy as np


class NoiseProcessMixin:

    def round_num(self, n, ndigits=0):
        p = 10**ndigits
        return (abs(n) * p * 2 + 1) // 2 / p * math.copysign(1, n)

    def round_arr(self, arr, decimals=0):
        return np.sign(arr) * np.floor(np.abs(arr) * 10**decimals + 0.5) / 10**decimals

    def adjust_noise_amount(self, img, density=0.5, sharpness=0.1):
        """Adjust the amount of the noise,
            for example, to convert the FBM noise into cloud cover.
            Args:
                arr (numpy.ndarray): noize image
                density, sharpness (float): less than 1.
        """

        img = img - img.min()
        img = img / img.max()
        img = 1 - np.e ** (-(img - density) * sharpness)
        img[img < 0] = 0

        # Scale between 0 to 255 and quantize
        img = img / img.max()
        img = self.round_arr(img * 255)

        # img = img.astype(np.uint8)
        # cv2.imwrite('temp.png', img)

        return img

    def reshape_noise_peak(self, arr, w=9, max_target=0.3, slope_control=5.5, bit8=True):
        """Transform a noise image with significant variations in height
            so that it becomes smooth. Supports both 8-bit and 16-bit images.
        """
        is_zero_mask = arr == 0

        # Convert to float64 and normalize to the range 0.0–1.0.
        max_val = 255. if bit8 else 65535.
        h_raw = arr.astype(np.float64) / max_val

        w = 9
        h_base = h_raw.copy()
        h_base = np.cumsum(h_base, axis=1)
        h_base[:, w:] = h_base[:, w:] - h_base[:, :-w]
        h_base = h_base / w
        h_base = np.cumsum(h_base, axis=0)
        h_base[w:, :] = h_base[w:, :] - h_base[:-w, :]
        h_base = h_base / w

        texture_detail = h_raw - h_base
        h_base_reshaped = max_target * (1.0 - np.exp(-h_base * slope_control))
        final_h = h_base_reshaped + texture_detail

        data_type = np.uint8 if bit8 else np.uint16
        result = (np.clip(final_h, 0.0, 1.0) * max_val).astype(data_type)

        result[is_zero_mask] = 0.
        return result