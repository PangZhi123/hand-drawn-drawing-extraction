from io import BytesIO

import fitz
from PIL import Image, ImageEnhance, ImageOps

from app.core.errors import DrawingError, UNREADABLE_IMAGE


def _prepare(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    gray = ImageOps.grayscale(image)
    return ImageEnhance.Contrast(gray).enhance(1.35)


def load_pages(content: bytes, suffix: str) -> list[Image.Image]:
    try:
        if suffix.lower() == ".pdf":
            document = fitz.open(stream=content, filetype="pdf")
            pages = []
            for page in document:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                pages.append(_prepare(Image.open(BytesIO(pixmap.tobytes("png")))))
            document.close()
            return pages
        return [_prepare(Image.open(BytesIO(content)))]
    except Exception as exc:
        raise DrawingError(*UNREADABLE_IMAGE) from exc
