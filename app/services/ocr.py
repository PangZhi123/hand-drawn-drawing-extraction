from abc import ABC, abstractmethod

from PIL import Image
import pytesseract
from pytesseract import Output

from app.domain.models import BoundingBox, ExtractedItem


class OCRBackend(ABC):
    @abstractmethod
    def recognize(self, image: Image.Image, source_file: str, page_number: int) -> list[ExtractedItem]:
        raise NotImplementedError


class TesseractOCRBackend(OCRBackend):
    def __init__(self, command: str | None = None, review_confidence: float = 0.70):
        if command:
            pytesseract.pytesseract.tesseract_cmd = command
        self.review_confidence = review_confidence

    def recognize(self, image: Image.Image, source_file: str, page_number: int) -> list[ExtractedItem]:
        data = pytesseract.image_to_data(image, lang="chi_sim+eng", output_type=Output.DICT)
        items: list[ExtractedItem] = []
        for index, raw_text in enumerate(data["text"]):
            text = raw_text.strip()
            if not text:
                continue
            raw_confidence = float(data["conf"][index])
            confidence = max(0.0, raw_confidence) / 100.0
            items.append(
                ExtractedItem(
                    text=text,
                    confidence=confidence,
                    source_file=source_file,
                    page_number=page_number,
                    bbox=BoundingBox(
                        x=int(data["left"][index]),
                        y=int(data["top"][index]),
                        width=int(data["width"][index]),
                        height=int(data["height"][index]),
                    ),
                    needs_review=confidence < self.review_confidence,
                )
            )
        return items
