import cv2
import numpy as np
from PIL import Image






#эта функция теперь в ImageTools



# def remove_white_space(img: Image):
#     np_img = np.array(img)
#     non_white_pixels = np.all(np_img < 248, axis=-1)
#     non_white_pixel_coords = np.where(non_white_pixels)
#     top_left = (np.min(non_white_pixel_coords[1]), np.min(non_white_pixel_coords[0]))
#     bottom_right = (np.max(non_white_pixel_coords[1]), np.max(non_white_pixel_coords[0]))
#     cropped_img = img.crop((top_left[0], top_left[1], bottom_right[0], bottom_right[1]))
#     return cropped_img












