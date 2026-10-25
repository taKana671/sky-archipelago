import pathlib
from datetime import datetime

import cv2


def make_dir(name, parent='.'):
    now = datetime.now()
    path = pathlib.Path(f'{parent}/{name}_{now.strftime("%Y%m%d%H%M%S")}')
    path.mkdir()
    return path


def output(arr, stem, parent='.', with_suffix=True):
    if with_suffix:
        now = datetime.now()
        stem = f'{stem}_{now.strftime("%Y%m%d%H%M%S")}'

    file_path = f'{parent}/{stem}.png'
    # file_name = f'{stem}_{now.strftime("%Y%m%d%H%M%S")}.{ext}'
    cv2.imwrite(file_path, arr)