"""
Image normalization utilities for converting images to bytes.
"""

import io
import PIL.Image  # type: ignore[import-untyped]


def safe_image_to_bytes(image: PIL.Image.Image, format: str = "JPEG") -> bytes:
    """
    Safely convert a PIL Image to bytes with error handling.

    Args:
        image: PIL Image object
        format: Image format (JPEG, PNG, etc.)

    Returns:
        Image data as bytes

    Raises:
        ValueError: If image conversion fails
    """
    try:
        if not isinstance(image, PIL.Image.Image):
            raise ValueError("Input must be a PIL Image object")

        # Convert to RGB if necessary for JPEG
        if format.upper() == "JPEG" and image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        buffer: io.BytesIO = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()

    except Exception as e:
        raise ValueError(f"Failed to convert image to bytes: {e}") from e


__all__ = ["safe_image_to_bytes"]
