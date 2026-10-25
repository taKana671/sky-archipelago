from enum import Enum


class SkyColor(Enum):

    SKYBLUE = ([0, 176, 240], [183, 236, 255])
    BLUE = ([1, 17, 104], [117, 169, 198])

    def __init__(self, start_color, end_color):
        self.start = start_color
        self.end = end_color

    def rgb_to_bgr(self):
        idx = [2, 1, 0]
        start_color = [self.start[i] for i in idx]
        end_color = [self.end[i] for i in idx]
        return start_color, end_color