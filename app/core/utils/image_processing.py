import cv2
import numpy as np


def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Converts an image to grayscale.
    Args:
        image (np.ndarray): The input image in OpenCV format (BGR).
    Returns:
        np.ndarray: The grayscale image.
    """
    if len(image.shape) == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def resize_image(
    image: np.ndarray,
    width: int | None = None,
    height: int | None = None,
    inter: int = cv2.INTER_AREA,
) -> np.ndarray:
    """
    Resizes an image to a specified width or height, maintaining aspect ratio.
    Args:
        image (np.ndarray): The input image.
        width (int, optional): Desired width. Defaults to None.
        height (int, optional): Desired height. Defaults to None.
        inter (int): Interpolation method. Defaults to cv2.INTER_AREA.
    Returns:
        np.ndarray: The resized image.
    Raises:
        ValueError: If neither width nor height is provided.
    """
    dim = None
    (h, w) = image.shape[:2]

    if width is None:
        if height is None:
            raise ValueError("Either width or height must be provided")
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))

    resized = cv2.resize(image, dim, interpolation=inter)
    return resized
