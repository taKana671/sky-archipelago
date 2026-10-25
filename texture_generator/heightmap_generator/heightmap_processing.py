import numpy as np
import cv2


class ProcessHeightmapMixin:

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

    def create_bw_texture_map(self, arr, threshold=0.0, blur=9):
        """Create a binary texture map in which areas with a luminance greater
           than the threshold are set to white.
            Args:
                arr (numpu.ndarray): A noise image.
                blur (int):
                    Specify None or an odd number.
                    Negative values are not allowed.
        """
        h, w = arr.shape[:2]
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[arr > threshold] = 255

        if blur:
            img = cv2.GaussianBlur(img, (9, 9), 0)

        return img