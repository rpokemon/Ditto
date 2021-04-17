import io

from PIL import Image  # type: ignore


__all__ = ("to_bytes",)


def to_bytes(image: Image.Image, /, format: str = "png") -> io.BytesIO:
    image_fp = io.BytesIO()
    image.save(image_fp, format=format)
    image_fp.seek(0)
    return image_fp
